"""
MarketMind AI — Stage 2: Embedding & Vector Store
Embeds chunks using BAAI/bge-base-en-v1.5 and stores in Chroma (dev)
or Pinecone (prod).

Embedding model: BAAI/bge-base-en-v1.5
  - 768 dimensions
  - Better than all-MiniLM-L6-v2 for domain-specific financial text
  - Free, runs locally, no API key needed

Vector store:
  - Chroma: local dev (persists to disk, easy to inspect)
  - Pinecone: production demo (cloud, shareable)
"""

import os
import time
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# EMBEDDING MODEL
# ─────────────────────────────────────────────

def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load BAAI/bge-base-en-v1.5 embedding model.
    First run downloads ~430MB. Cached locally after that.

    Why BGE over MiniLM:
      - 768 dims vs 384 dims → richer representation
      - Trained on finance/legal text → better for SEBI/NSE language
      - MTEB score: 63.5 vs 56.2 for retrieval tasks
    """
    print("[Embeddings] Loading BAAI/bge-base-en-v1.5 ...")
    model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},   # switch to "cuda" if GPU available
        encode_kwargs={
            "normalize_embeddings": True,  # required for BGE cosine similarity
            "batch_size": 32,
        },
    )
    print("[Embeddings] Model loaded.")
    return model


# ─────────────────────────────────────────────
# CHROMA — LOCAL VECTOR STORE (development)
# ─────────────────────────────────────────────

CHROMA_PERSIST_DIR = "./chroma_db"


def get_chroma_store(embedding_model: HuggingFaceEmbeddings) -> Chroma:
    """
    Connect to local Chroma vector store.
    Creates the DB if it doesn't exist. Loads existing if it does.
    Data persists to disk at CHROMA_PERSIST_DIR.
    """
    store = Chroma(
        collection_name="marketmind",
        embedding_function=embedding_model,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    print(f"[Chroma] Connected. Collection: marketmind | Dir: {CHROMA_PERSIST_DIR}")
    return store


def upsert_to_chroma(
    chunks: list[Document],
    store: Chroma,
    batch_size: int = 100,
) -> None:
    """
    Embed and upsert chunks into Chroma in batches.
    Generates a stable ID per chunk so re-runs don't create duplicates.
    """
    import hashlib

    def make_id(doc: Document) -> str:
        """Stable ID = hash of content + source + chunk_index."""
        raw = f"{doc.page_content}{doc.metadata.get('source','')}{doc.metadata.get('chunk_index',0)}"
        return hashlib.md5(raw.encode()).hexdigest()

    ids = [make_id(c) for c in chunks]
    texts = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]

    total = len(chunks)
    print(f"\n[Chroma] Upserting {total} chunks in batches of {batch_size} ...")

    for i in range(0, total, batch_size):
        batch_ids = ids[i:i + batch_size]
        batch_texts = texts[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]

        store.add_texts(texts=batch_texts, metadatas=batch_meta, ids=batch_ids)
        print(f"  Upserted {min(i + batch_size, total)}/{total}")
        time.sleep(0.1)  # avoid CPU spike

    print(f"[Chroma] Done. Total vectors in store: {store._collection.count()}")


# ─────────────────────────────────────────────
# PINECONE — CLOUD VECTOR STORE (production/demo)
# ─────────────────────────────────────────────

def get_pinecone_store(embedding_model: HuggingFaceEmbeddings):
    """
    Connect to Pinecone vector store.
    Requires PINECONE_API_KEY in .env.

    Index settings:
      - Name: marketmind
      - Dimension: 768  (matches BAAI/bge-base-en-v1.5)
      - Metric: cosine
      - Cloud: aws, Region: us-east-1 (free tier)
    """
    from pinecone import Pinecone, ServerlessSpec
    from langchain_pinecone import PineconeVectorStore

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not set in .env")

    pc = Pinecone(api_key=api_key)
    index_name = os.getenv("PINECONE_INDEX", "marketmind")

    # Create index if it doesn't exist
    existing = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing:
        print(f"[Pinecone] Creating index '{index_name}' with dim=768, metric=cosine ...")
        pc.create_index(
            name=index_name,
            dimension=768,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print("[Pinecone] Index created.")

    store = PineconeVectorStore(
        index=pc.Index(index_name),
        embedding=embedding_model,
        text_key="page_content",
    )
    print(f"[Pinecone] Connected to index: {index_name}")
    return store


def upsert_to_pinecone(
    chunks: list[Document],
    store,
    batch_size: int = 50,
) -> None:
    """
    Embed and upsert chunks into Pinecone in batches.
    Pinecone free tier: max 100k vectors, 5 req/sec.
    """
    total = len(chunks)
    print(f"\n[Pinecone] Upserting {total} chunks in batches of {batch_size} ...")

    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        store.add_documents(batch)
        print(f"  Upserted {min(i + batch_size, total)}/{total}")
        time.sleep(0.5)  # Pinecone rate limit safety

    print(f"[Pinecone] Upsert complete.")


# ─────────────────────────────────────────────
# RETRIEVAL — used by RAG service later
# ─────────────────────────────────────────────

def get_retriever(store, search_kwargs: dict = None):
    """
    Return a LangChain retriever from the vector store.
    Default: top-5 results, MMR (Maximum Marginal Relevance)
    to balance relevance with diversity.

    MMR prevents the retriever from returning 5 near-identical chunks
    from the same SEBI filing — it spreads results across sources.
    """
    return store.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs or {
            "k": 5,           # return top 5
            "fetch_k": 20,    # fetch 20 candidates before MMR re-ranking
            "lambda_mult": 0.6,  # 0=max diversity, 1=max relevance
        },
    )


# ─────────────────────────────────────────────
# MASTER STAGE 2 RUNNER
# ─────────────────────────────────────────────

def run_embedding_pipeline(
    chunks: list[Document],
    use_pinecone: bool = False,
):
    """
    Full Stage 2 pipeline: embed chunks and upsert to vector store.

    Args:
        chunks: output of stage1 chunker.chunk_documents()
        use_pinecone: True for prod/demo, False for local dev

    Returns:
        (store, retriever) — ready for the RAG service
    """
    embedding_model = get_embedding_model()

    if use_pinecone:
        store = get_pinecone_store(embedding_model)
        upsert_to_pinecone(chunks, store)
    else:
        store = get_chroma_store(embedding_model)
        upsert_to_chroma(chunks, store)

    retriever = get_retriever(store)
    print("\n[Stage 2 complete] Vector store ready for retrieval.")
    return store, retriever


if __name__ == "__main__":
    # Quick smoke test with 2 dummy chunks
    sample_chunks = [
        Document(
            page_content="SEBI Filing: Tata Power bulk deal. Promoter bought 12L shares at ₹420. Bullish signal.",
            metadata={"type": "bulk_deal", "source": "bse_bulk_deals", "ticker": "TATAPOWER"},
        ),
        Document(
            page_content="Stock: RELIANCE | Price: ₹2,940 | Day change: +1.2% | Market cap: ₹1,98,000 Cr",
            metadata={"type": "price", "source": "yfinance", "ticker": "RELIANCE"},
        ),
    ]

    store, retriever = run_embedding_pipeline(sample_chunks, use_pinecone=False)

    # Test retrieval
    results = retriever.invoke("What is the bulk deal for Tata Power?")
    print(f"\n[Test retrieval] Query: 'What is the bulk deal for Tata Power?'")
    for r in results:
        print(f"  → {r.page_content[:100]}")