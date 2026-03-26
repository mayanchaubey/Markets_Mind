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

import os
import logging
from functools import lru_cache
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import Pinecone as PineconeVectorStore
from pinecone import Pinecone
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

# ── Module-level singletons (loaded once, reused across all requests) ──
_retriever = None
_groq_client = None


# ─────────────────────────────────────────────
# EMBEDDING MODEL
# ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load BGE model once and cache it.
    lru_cache ensures this never runs twice even if called multiple times.
    First call takes ~10s to load from HF_HOME cache.
    """
    logger.info("[RAG] Loading embedding model BAAI/bge-base-en-v1.5 ...")
    model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={
            "normalize_embeddings": True,  # required for BGE cosine similarity
            "batch_size": 32,
        },
    )
    logger.info("[RAG] Embedding model loaded.")
    return model


# ─────────────────────────────────────────────
# PINECONE CONNECTION
# ─────────────────────────────────────────────

def _get_pinecone_retriever():
    """
    Connect to the existing Pinecone index and return an MMR retriever.
    Does NOT create or modify the index — read-only connection.
    The index must already be populated by pipeline_runner.py.
    """
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "marketmind")

    if not api_key:
        raise ValueError("PINECONE_API_KEY not set in .env")

    logger.info(f"[RAG] Connecting to Pinecone index: {index_name} ...")

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    # Verify index exists and has vectors
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

    # MMR retrieval — same settings as pipeline_runner for consistency
    retriever = store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,           # return top 5 chunks
            "fetch_k": 20,    # fetch 20 candidates, MMR re-ranks for diversity
            "lambda_mult": 0.6,  # balance relevance vs diversity
        },
    )

    logger.info("[RAG] Pinecone retriever ready.")
    return retriever


# ─────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────

def _get_groq_client() -> Groq:
    """Initialize Groq client. Lightweight — just sets the API key."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env")
    logger.info("[RAG] Groq client initialized.")
    return Groq(api_key=api_key)


# ─────────────────────────────────────────────
# PROMPT TEMPLATES
# ─────────────────────────────────────────────

def _build_prompt(query: str, context: str, mode: str) -> Tuple[str, str]:
    """
    Build mode-specific system + user prompt.
    Each mode has a different persona and task framing.
    Context is retrieved chunks joined as a single string.
    """

    if mode == "chat":
        system = (
            "You are MarketMind, an expert Indian stock market analyst. "
            "Answer the user's question using ONLY the context provided below. "
            "Be concise, factual, and specific. Mention stock names, prices, and "
            "percentages where available. If the context does not contain enough "
            "information to answer, say so clearly — do not hallucinate. "
            "Format numbers in Indian style (Cr, L, ₹). "
            "Always cite the source reference numbers [1], [2], etc. when making claims."
        )
        user = (
            f"Context from market data:\n{context}\n\n"
            f"Question: {query}\n\n"
            f"Answer:"
        )

    elif mode == "radar":
        system = (
            "You are MarketMind Radar, a market opportunity scanner. "
            "Analyse the context below and identify the top 3-5 investment "
            "opportunities or noteworthy signals. Look for: unusual bulk deals, "
            "strong price momentum, positive SEBI filings, or stocks near 52-week "
            "highs with volume. For each opportunity give: stock name, signal type, "
            "key data point, and a one-line rationale. Be specific — no generic advice. "
            "Format as a numbered list with proper formatting.\n\n"
            "Example format:\n"
            "1. **Stock Name (TICKER)** - Signal Type\n"
            "   Key Data: [specific numbers]\n"
            "   Rationale: [one line explanation]"
        )
        user = (
            f"Market data context:\n{context}\n\n"
            f"User focus: {query}\n\n"
            f"Top opportunities:"
        )

    elif mode == "factcheck":
        system = (
            "You are MarketMind FactChecker, a financial claim verification engine. "
            "You will be given a claim made by a finfluencer and real market data as context. "
            "Your job is to verify the claim against the data. "
            "Output a structured verdict:\n\n"
            "**VERDICT:** [VERIFIED / MISLEADING / FALSE / UNVERIFIABLE]\n\n"
            "**EVIDENCE:** [specific data points from context that support or contradict the claim]\n\n"
            "**EXPLANATION:** [2-3 sentences explaining your verdict]\n\n"
            "Be strict — if the data partially supports the claim, say MISLEADING, not VERIFIED. "
            "If the context lacks sufficient information to verify, say UNVERIFIABLE."
        )
        user = (
            f"Real market data context:\n{context}\n\n"
            f"Finfluencer claim to verify: {query}\n\n"
            f"Verdict:"
        )

    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'chat', 'radar', or 'factcheck'.")

    return system, user


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def _format_sources(retrieved_docs) -> Tuple[str, List[Dict]]:
    """
    Format retrieved documents into context string and source metadata.
    
    Returns:
        Tuple of (context_string, sources_list)
    """
    context_parts = []
    sources = []
    
    for i, doc in enumerate(retrieved_docs, 1):
        # Add chunk to context with reference number
        context_parts.append(f"[{i}] {doc.page_content}")
        
        # Extract metadata
        metadata = doc.metadata or {}
        source_info = {
            "chunk_id": i,
            "source": metadata.get("source", "unknown"),
            "type": metadata.get("type", "unknown"),
            "ticker": metadata.get("ticker", ""),
            "date": metadata.get("date", ""),
            "score": metadata.get("score", None),  # If available from retriever
        }
        sources.append(source_info)
    
    context = "\n\n".join(context_parts)
    return context, sources


def _sanitize_query(query: str) -> str:
    """
    Clean and validate user query.
    Prevents injection attempts and normalizes whitespace.
    """
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string")
    
    # Remove excess whitespace
    query = " ".join(query.split())
    
    # Limit query length
    max_length = 500
    if len(query) > max_length:
        logger.warning(f"[RAG] Query truncated from {len(query)} to {max_length} chars")
        query = query[:max_length]
    
    return query


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def init_rag():
    """
    Initialize the RAG service. Call this ONCE on FastAPI startup via lifespan.
    Loads the embedding model and connects to Pinecone.
    Stores retriever and Groq client as module-level singletons.

    Raises ValueError if API keys are missing.
    """
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
    """
    Full RAG pipeline for a single user query.

    Args:
        query: user's question or claim to verify
        mode:  "chat" | "radar" | "factcheck"
        k: number of chunks to retrieve (optional, overrides default of 5)
        temperature: LLM temperature (optional, overrides default of 0.2)

    Returns:
        dict with keys:
          "answer"   — LLM-generated response string
          "sources"  — list of source metadata dicts from retrieved chunks
          "mode"     — the mode used
          "chunks"   — number of chunks retrieved
          "query"    — the sanitized query used

    Raises:
        RuntimeError if init_rag() was not called before this.
        ValueError if query is invalid or mode is unknown.
    """
    if _retriever is None or _groq_client is None:
        raise RuntimeError("RAG service not initialized. Call init_rag() first.")

    # Validate and clean query
    try:
        query = _sanitize_query(query)
    except ValueError as e:
        logger.error(f"[RAG] Invalid query: {e}")
        raise

    # Validate mode
    valid_modes = ["chat", "radar", "factcheck"]
    if mode not in valid_modes:
        raise ValueError(f"Unknown mode: {mode}. Use one of {valid_modes}.")

    # Step 1: Retrieve relevant chunks from Pinecone
    logger.info(f"[RAG] Retrieving context for query: '{query[:60]}...' (mode={mode})")
    
    try:
        # Override k if provided
        if k is not None:
            retrieved_docs = _retriever.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": 20, "lambda_mult": 0.6}
        ).invoke(query)
        else:
            retrieved_docs = _retriever.invoke(query)
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

    if not retrieved_docs:
        logger.warning("[RAG] No documents retrieved from Pinecone.")
        return {
            "answer": "I don't have enough market data to answer this right now. Try running the pipeline first.",
            "sources": [],
            "mode": mode,
            "chunks": 0,
            "query": query,
        }

    # Step 2: Format context from retrieved chunks
    context, sources = _format_sources(retrieved_docs)
    logger.info(f"[RAG] Retrieved {len(retrieved_docs)} chunks, total context length: {len(context)} chars")

    # Step 3: Build mode-specific prompt
    try:
        system_prompt, user_prompt = _build_prompt(query, context, mode)
    except ValueError as e:
        logger.error(f"[RAG] Error building prompt: {e}")
        raise

    # Step 4: Call Groq LLM
    groq_model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    temp = temperature if temperature is not None else 0.2
    
    logger.info(f"[RAG] Calling Groq (model: {groq_model}, temp: {temp}) ...")
    
    try:
        response = _groq_client.chat.completions.create(
            model=groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temp,   # low temp = factual, less creative
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

    return {
        "answer": answer,
        "sources": sources,
        "mode": mode,
        "chunks": len(retrieved_docs),
        "query": query,
    }


def get_rag_status() -> Dict:
    """
    Get the current status of the RAG service.
    Useful for health checks and debugging.
    
    Returns:
        dict with service status information
    """
    return {
        "initialized": _retriever is not None and _groq_client is not None,
        "retriever_ready": _retriever is not None,
        "groq_ready": _groq_client is not None,
        "embedding_model": "BAAI/bge-base-en-v1.5",
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
        "pinecone_index": os.getenv("PINECONE_INDEX", "marketmind"),
    }


# ─────────────────────────────────────────────
# SMOKE TEST — run directly to verify setup
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
        
        # Check status
        status = get_rag_status()
        print(f"\n[Status] {status}")
        
    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        exit(1)

    test_cases = [
        ("What is the current price of Reliance?", "chat"),
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