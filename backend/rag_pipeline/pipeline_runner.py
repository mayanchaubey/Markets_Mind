"""
MarketMind AI — Pipeline Runner
Orchestrates Stage 1 (ingestion + cleaning + chunking)
and Stage 2 (embedding + vector store).

Run daily via scheduler.py or manually.
Writes logs to backend/pipeline.log
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Logging setup — writes to both console AND pipeline.log ──
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ── Path fix for running as module ───────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline.stage1_ingestion.ingestion import run_ingestion
from rag_pipeline.stage1_ingestion.preprocessing import run_cleaning
from rag_pipeline.stage1_ingestion.chunker import chunk_documents
from rag_pipeline.stage2_embedding.embedder import run_embedding_pipeline


# ── Metrics file — tracks every pipeline run ─────────────────
METRICS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "pipeline_metrics.json"
)


def _load_metrics() -> list:
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "r") as f:
            return json.load(f)
    return []


def _save_metrics(metrics: list):
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=2)


def _is_first_run() -> bool:
    """Check if historical data has ever been loaded."""
    metrics = _load_metrics()
    return not any(m.get("historical_loaded") for m in metrics)


def run_full_pipeline(
    youtube_videos: list[dict] = None,
    bse_csv_path: str = None,
    use_pinecone: bool = False,
    force_historical: bool = False,
):
    """
    Full RAG pipeline: ingest → clean → chunk → embed → store.

    Args:
        youtube_videos:   list of {"url", "title", "channel"}
        bse_csv_path:     path to BSE bulk deals CSV
        use_pinecone:     False = Chroma (local), True = Pinecone (team/demo)
        force_historical: force reload of 1yr historical data
    """
    run_start = datetime.now()

    logger.info("=" * 55)
    logger.info("  MarketMind AI — RAG Pipeline Starting")
    logger.info(f"  Run started at: {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 55)

    # Detect first run automatically
    is_first = _is_first_run() or force_historical
    if is_first:
        logger.info("[First run detected] Will load 1 year historical price data.")

    # ── Stage 1a: Ingestion ──────────────────────────────────
    logger.info("\n[Stage 1a] Ingesting raw data from all sources...")
    raw_docs = run_ingestion(
        youtube_videos=youtube_videos,
        bse_csv_path=bse_csv_path,
        load_historical=is_first,
    )

    source_counts = {}
    for doc in raw_docs:
        src = doc.metadata.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    logger.info(f"[Stage 1a] Source breakdown:")
    for src, count in sorted(source_counts.items()):
        logger.info(f"  {src}: {count} docs")

    # ── Stage 1b: Cleaning ──────────────────────────────────
    logger.info("\n[Stage 1b] Cleaning and filtering documents...")
    clean_docs = run_cleaning(raw_docs)

    if not clean_docs:
        logger.warning("[WARN] No clean documents produced. Check data sources.")
        return None, None

    # ── Stage 1c: Chunking ──────────────────────────────────
    logger.info("\n[Stage 1c] Chunking documents...")
    chunks = chunk_documents(clean_docs)

    chunk_type_counts = {}
    for chunk in chunks:
        t = chunk.metadata.get("type", "unknown")
        chunk_type_counts[t] = chunk_type_counts.get(t, 0) + 1

    logger.info(f"[Stage 1c] Chunk breakdown:")
    for t, count in sorted(chunk_type_counts.items()):
        logger.info(f"  {t}: {count} chunks")

    # ── Stage 2: Embedding + Vector Store ───────────────────
    logger.info("\n[Stage 2] Embedding and storing chunks...")
    store, retriever = run_embedding_pipeline(chunks, use_pinecone=use_pinecone)

    # ── Metrics ─────────────────────────────────────────────
    run_end = datetime.now()
    duration_sec = (run_end - run_start).seconds

    run_metrics = {
        "run_time": run_start.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": duration_sec,
        "raw_docs": len(raw_docs),
        "clean_docs": len(clean_docs),
        "chunks": len(chunks),
        "source_breakdown": source_counts,
        "chunk_breakdown": chunk_type_counts,
        "vector_store": "pinecone" if use_pinecone else "chroma",
        "historical_loaded": is_first,
    }

    all_metrics = _load_metrics()
    all_metrics.append(run_metrics)
    _save_metrics(all_metrics)

    # ── Summary ─────────────────────────────────────────────
    logger.info("\n" + "=" * 55)
    logger.info("  Pipeline Complete!")
    logger.info(f"  Raw docs:      {len(raw_docs)}")
    logger.info(f"  Clean docs:    {len(clean_docs)}")
    logger.info(f"  Chunks:        {len(chunks)}")
    logger.info(f"  Vectors:       {len(chunks)}")
    logger.info(f"  Store:         {'Pinecone' if use_pinecone else 'Chroma (local)'}")
    logger.info(f"  Duration:      {duration_sec}s")
    logger.info(f"  Log file:      {LOG_FILE}")
    logger.info(f"  Metrics file:  {METRICS_FILE}")
    logger.info("=" * 55)

    return store, retriever


def print_metrics_summary():
    """Print a summary of all pipeline runs. Call this anytime to see history."""
    metrics = _load_metrics()
    if not metrics:
        print("No pipeline runs recorded yet.")
        return

    print(f"\n{'='*55}")
    print(f"  Pipeline Run History ({len(metrics)} runs)")
    print(f"{'='*55}")
    for m in metrics[-10:]:  # show last 10 runs
        print(f"\n  Run: {m['run_time']} ({m['duration_seconds']}s)")
        print(f"  Docs: {m['raw_docs']} raw → {m['clean_docs']} clean → {m['chunks']} chunks")
        print(f"  Store: {m['vector_store']}")
        if m.get("source_breakdown"):
            for src, count in m["source_breakdown"].items():
                print(f"    [{src}]: {count}")


if __name__ == "__main__":
    use_pinecone = os.getenv("VECTOR_STORE", "chroma").lower() == "pinecone"

    store, retriever = run_full_pipeline(
        youtube_videos=[
            # Add real finfluencer YouTube URLs here
            # {
            #   "url": "https://www.youtube.com/watch?v=VIDEO_ID",
            #   "title": "Top stocks 2026",
            #   "channel": "Akshat Shrivastava"
            # },
        ],
        bse_csv_path="data/bse_bulk_deals.csv",         # set to "data/bse_bulk_deals.csv" if you have it
        use_pinecone=use_pinecone,
        force_historical=False,   # set True ONCE to load 1yr history
    )

    if retriever:
        print(f"\n[Test retrieval]")
        results = retriever.invoke("What is today's FII activity?")
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r.metadata.get('source','?')}] {r.page_content[:100]}")

    print_metrics_summary()