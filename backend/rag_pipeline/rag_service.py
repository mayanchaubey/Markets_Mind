"""
MarketMind AI — Stage 3: RAG Service
The core reasoning layer. Connects Pinecone retriever to Groq LLM.

Exposes two public functions:
  init_rag()                   → call once on FastAPI startup
  generate_answer(query, mode) → call per user request

Modes:
  "chat"      → general market Q&A
  "radar"     → surface investment opportunities from stored data
  "factcheck" → verify a finfluencer claim against real market data
"""

"""
MarketMind AI — Stage 3: RAG Service (Optimized)
"""

from pathlib import Path
import os

cache_dir = Path(__file__).resolve().parent.parent / ".hf_cache"
os.environ["HF_HOME"] = str(cache_dir)

import logging
import time
from functools import lru_cache
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

_retriever = None
_groq_client = None

# ── Simple in-memory cache to prevent duplicate calls ──
_response_cache: Dict[str, Dict] = {}
_cache_ttl = 300  # 5 minutes


def _get_cache_key(query: str, mode: str) -> str:
    return f"{mode}:{query.lower().strip()[:100]}"


def _get_cached(query: str, mode: str) -> Optional[Dict]:
    key = _get_cache_key(query, mode)
    if key in _response_cache:
        cached = _response_cache[key]
        if time.time() - cached["_timestamp"] < _cache_ttl:
            logger.info(f"[RAG] Cache hit for query (mode={mode})")
            return cached["data"]
        else:
            del _response_cache[key]
    return None


def _set_cached(query: str, mode: str, data: Dict):
    key = _get_cache_key(query, mode)
    _response_cache[key] = {"data": data, "_timestamp": time.time()}


# ─────────────────────────────────────────────
# EMBEDDING MODEL
# ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_embedding_model() -> HuggingFaceEmbeddings:
    logger.info("[RAG] Loading embedding model BAAI/bge-base-en-v1.5 ...")
    model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={
            "normalize_embeddings": True,
            "batch_size": 32,
        },
    )
    logger.info("[RAG] Embedding model loaded.")
    return model


# ─────────────────────────────────────────────
# PINECONE CONNECTION
# ─────────────────────────────────────────────

def _get_pinecone_retriever():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "marketmind")

    if not api_key:
        raise ValueError("PINECONE_API_KEY not set in .env")

    logger.info(f"[RAG] Connecting to Pinecone index: {index_name} ...")

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    try:
        stats = index.describe_index_stats()
        vector_count = stats.total_vector_count
        logger.info(f"[RAG] Pinecone index stats: {vector_count} vectors")
        if vector_count == 0:
            logger.warning("[RAG] Pinecone index is empty! Run pipeline_runner.py first.")
    except Exception as e:
        logger.error(f"[RAG] Error checking Pinecone index: {e}")

    embedding_model = _get_embedding_model()

    store = PineconeVectorStore(
        index=index,
        embedding=embedding_model,
        text_key="page_content",
    )

    retriever = store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,
            "fetch_k": 20,
            "lambda_mult": 0.6,
        },
    )

    logger.info("[RAG] Pinecone retriever ready.")
    return retriever


# ─────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────

def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env")
    logger.info("[RAG] Groq client initialized.")
    return Groq(api_key=api_key)


# ─────────────────────────────────────────────
# QUERY ROUTING — RAG vs Direct LLM
# ─────────────────────────────────────────────

STOCK_KEYWORDS = [
    "stock", "share", "price", "nifty", "sensex", "bse", "nse", "sebi",
    "market", "invest", "portfolio", "buy", "sell", "hold", "rally",
    "crash", "ipo", "fii", "dii", "bulk deal", "reliance", "tcs",
    "hdfc", "infosys", "icici", "sbi", "bajaj", "titan", "wipro",
    "rupee", "crore", "lakh", "pe ratio", "earnings", "revenue",
    "quarterly", "annual", "dividend", "bonus", "split", "mutual fund",
    "etf", "smallcap", "midcap", "largecap", "bluechip", "sector",
]


def _should_use_rag(query: str) -> bool:
    """
    Returns True if query needs RAG (stock/market specific).
    Returns False if it's a general question — direct LLM is better.
    """
    query_lower = query.lower()
    return any(kw in query_lower for kw in STOCK_KEYWORDS)


# ─────────────────────────────────────────────
# PROMPT TEMPLATES — Upgraded
# ─────────────────────────────────────────────

def _build_prompt(query: str, context: str, mode: str) -> Tuple[str, str]:

    if mode == "chat":
        if context:
            system = (
                "You are MarketMind, a professional financial analyst specializing in Indian stock markets. "
                "You provide expert-level analysis backed by real market data.\n\n"
                "Instructions:\n"
                "- Give clear, structured answers with bullet points where helpful\n"
                "- Explain concepts in simple terms with examples\n"
                "- Always mention specific stock names, prices (₹), and percentages from the context\n"
                "- Format numbers in Indian style (₹, Cr, L)\n"
                "- Cite source references [1], [2], etc. when making specific claims\n"
                "- If context is insufficient, say 'based on available data' — do NOT hallucinate\n"
                "- End with a brief 1-line actionable insight when possible"
            )
            user = (
                f"Market Data Context:\n{context[:1200]}\n\n"
                f"User Question: {query}\n\n"
                f"Professional Analysis:"
            )
        else:
            # No RAG — direct LLM for general questions
            system = (
                "You are MarketMind, a professional financial analyst specializing in Indian stock markets. "
                "Answer the question clearly and concisely. Use bullet points where helpful. "
                "Format numbers in Indian style (₹, Cr, L). "
                "If you don't have specific current data, give general expert guidance and say so."
            )
            user = f"Question: {query}\n\nAnswer:"

    elif mode == "radar":
        system = (
            "You are MarketMind Radar, an elite market opportunity scanner for Indian equities. "
            "Analyse the context and identify the top 3-5 investment signals.\n\n"
            "For each opportunity provide:\n"
            "1. **Stock Name (TICKER)** - Signal Type (BULLISH/BEARISH/NEUTRAL)\n"
            "   Key Data: [specific price, % change, or volume numbers]\n"
            "   Rationale: [one precise sentence explaining the signal]\n\n"
            "Rules:\n"
            "- Use ONLY data from the context — no generic statements\n"
            "- Each signal must have a specific ticker and number\n"
            "- Be direct and actionable — no filler text"
        )
        user = (
            f"Market Data Context:\n{context[:1500]}\n\n"
            f"Scan focus: {query}\n\n"
            f"Top Investment Signals:"
        )

    elif mode == "factcheck":
        system = (
            "You are MarketMind FactChecker, a financial claim verification engine. "
            "Verify the finfluencer claim against real market data strictly.\n\n"
            "Output format (use exactly this structure):\n\n"
            "**VERDICT:** [VERIFIED / MISLEADING / FALSE / UNVERIFIABLE]\n\n"
            "**EVIDENCE:** [Quote specific numbers from context that prove or disprove the claim]\n\n"
            "**EXPLANATION:** [2-3 sentences. Be specific about what matches and what doesn't]\n\n"
            "Verdict rules:\n"
            "- VERIFIED: claim is fully supported by data\n"
            "- MISLEADING: partially true but missing important context\n"
            "- FALSE: claim directly contradicts the data\n"
            "- UNVERIFIABLE: insufficient data to judge"
        )
        user = (
            f"Real Market Data:\n{context[:1200]}\n\n"
            f"Finfluencer Claim: {query}\n\n"
            f"Verdict:"
        )

    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'chat', 'radar', or 'factcheck'.")

    return system, user


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def _format_sources(retrieved_docs) -> Tuple[str, List[Dict]]:
    context_parts = []
    sources = []

    for i, doc in enumerate(retrieved_docs, 1):
        context_parts.append(f"[{i}] {doc.page_content}")
        metadata = doc.metadata or {}
        source_info = {
            "chunk_id": i,
            "source": metadata.get("source", "unknown"),
            "type": metadata.get("type", "unknown"),
            "ticker": metadata.get("ticker", ""),
            "date": metadata.get("date", ""),
            "score": metadata.get("score", None),
        }
        sources.append(source_info)

    context = "\n\n".join(context_parts)
    return context, sources


def _sanitize_query(query: str) -> str:
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string")
    query = " ".join(query.split())
    max_length = 500
    if len(query) > max_length:
        logger.warning(f"[RAG] Query truncated from {len(query)} to {max_length} chars")
        query = query[:max_length]
    return query


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def init_rag():
    global _retriever, _groq_client
    logger.info("[RAG] Initializing RAG service ...")
    try:
        _retriever = _get_pinecone_retriever()
        _groq_client = _get_groq_client()
        logger.info("[RAG] ✓ RAG service ready.")
    except Exception as e:
        logger.error(f"[RAG] ✗ Failed to initialize RAG service: {e}")
        raise


def generate_answer(
    query: str,
    mode: str = "chat",
    k: Optional[int] = None,
    temperature: Optional[float] = None
) -> Dict:
    if _retriever is None or _groq_client is None:
        raise RuntimeError("RAG service not initialized. Call init_rag() first.")

    try:
        query = _sanitize_query(query)
    except ValueError as e:
        logger.error(f"[RAG] Invalid query: {e}")
        raise

    valid_modes = ["chat", "radar", "factcheck"]
    if mode not in valid_modes:
        raise ValueError(f"Unknown mode: {mode}. Use one of {valid_modes}.")

    # Check cache first — prevents duplicate parallel calls
    cached = _get_cached(query, mode)
    if cached:
        return cached

    # Smart routing — skip RAG for general questions in chat mode
    use_rag = True
    if mode == "chat" and not _should_use_rag(query):
        use_rag = False
        logger.info(f"[RAG] General question detected — skipping Pinecone retrieval")

    retrieved_docs = []
    context = ""
    sources = []

    if use_rag:
        logger.info(f"[RAG] Retrieving context for query: '{query[:60]}...' (mode={mode})")
        try:
            if k is not None:
                retrieved_docs = _retriever.vectorstore.as_retriever(
                    search_type="mmr",
                    search_kwargs={"k": k, "fetch_k": 20, "lambda_mult": 0.6}
                ).invoke(query)
            else:
                retrieved_docs = _retriever.invoke(query)

            context, sources = _format_sources(retrieved_docs)
            logger.info(f"[RAG] Retrieved {len(retrieved_docs)} chunks, context length: {len(context)} chars")

        except Exception as e:
            logger.error(f"[RAG] Error retrieving from Pinecone: {e}")
            return {
                "answer": "Error retrieving market data. Please try again later.",
                "sources": [],
                "mode": mode,
                "chunks": 0,
                "query": query,
                "error": str(e)
            }

    # Build prompt
    try:
        system_prompt, user_prompt = _build_prompt(query, context, mode)
    except ValueError as e:
        logger.error(f"[RAG] Error building prompt: {e}")
        raise

    # Call Groq
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    temp = temperature if temperature is not None else 0.2

    logger.info(f"[RAG] Calling Groq (model: {groq_model}, temp: {temp}) ...")

    try:
        response = _groq_client.chat.completions.create(
            model=groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temp,
            max_tokens=1024,
            stream=False,
        )

        answer = response.choices[0].message.content.strip()
        logger.info(f"[RAG] ✓ Answer generated ({len(answer)} chars).")

    except Exception as e:
        logger.error(f"[RAG] Error calling Groq API: {e}")
        return {
            "answer": "Error generating response. Please try again later.",
            "sources": sources,
            "mode": mode,
            "chunks": len(retrieved_docs),
            "query": query,
            "error": str(e)
        }

    result = {
        "answer": answer,
        "sources": sources,
        "mode": mode,
        "chunks": len(retrieved_docs),
        "query": query,
    }

    # Cache the result
    _set_cached(query, mode, result)

    return result


def get_rag_status() -> Dict:
    return {
        "initialized": _retriever is not None and _groq_client is not None,
        "retriever_ready": _retriever is not None,
        "groq_ready": _groq_client is not None,
        "embedding_model": "BAAI/bge-base-en-v1.5",
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "pinecone_index": os.getenv("PINECONE_INDEX", "marketmind"),
        "cache_size": len(_response_cache),
    }


# ─────────────────────────────────────────────
# SMOKE TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("[Smoke Test] Initializing RAG service...")
    print("="*60)

    try:
        init_rag()
        status = get_rag_status()
        print(f"\n[Status] {status}")
    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        exit(1)

    test_cases = [
        ("What is the current price of Reliance?", "chat"),
        ("How does a stock market work?", "chat"),
        ("What investment opportunities do you see today?", "radar"),
        ("Reliance will hit ₹4000 by next month based on strong fundamentals", "factcheck"),
    ]

    for query, mode in test_cases:
        print(f"\n{'='*60}")
        print(f"Mode:  {mode.upper()}")
        print(f"Query: {query}")
        print("="*60)
        try:
            result = generate_answer(query, mode)
            print(f"\nAnswer:\n{result['answer']}")
            print(f"\nSources ({result['chunks']} chunks):")
            for s in result["sources"]:
                print(f"  [{s['chunk_id']}] {s['type']} | {s['ticker']} | {s['date']} | {s['source']}")
        except Exception as e:
            print(f"✗ Error: {e}")

    print(f"\n{'='*60}")
    print("[Smoke Test] Complete!")
    print("="*60)
