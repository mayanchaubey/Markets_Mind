# MarketMind AI

<p align="center">
  <img src="https://img.shields.io/badge/RAG-System-blue" />
  <img src="https://img.shields.io/badge/LLM-Groq-orange" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-green" />
  <img src="https://img.shields.io/badge/VectorDB-Pinecone-purple" />
</p>

<p align="center">
  <b>AI-powered Indian Stock Market Intelligence Platform</b><br/>
  Real-time insights • Opportunity detection • Fact-checking
</p>

---


## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the Pipeline](#running-the-pipeline)
- [Running the API Server](#running-the-api-server)
- [API Reference](#api-reference)
- [Data Sources](#data-sources)
- [Pipeline Design](#pipeline-design)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## Overview

MarketMind AI answers questions about the Indian stock market by grounding every response in real, retrieved data — not hallucinated knowledge. It ingests live NSE prices, ET Markets news, SEBI filings, BSE bulk deals, and YouTube finfluencer transcripts daily, embeds them into a vector store, and serves answers through a FastAPI backend connected to Groq's LLM inference.

The project was built for a hackathon and is structured to be extended into a production product.

---

## Features

### Market Chat
A conversational terminal for stock analysis. Users ask questions in natural language — "What is the FII activity this week?" or "Analyze HDFC Bank" — and receive answers grounded in retrieved market data with cited sources.

### Opportunity Radar
Scans the vector store for investment signals: unusual bulk deals, stocks near 52-week highs, strong price momentum, and positive regulatory filings. Surfaces the top 3-5 opportunities with rationale and key data points.

### Finfluencer Fact-Checker
Users paste any YouTube URL. The system fetches the transcript, extracts financial claims, and verifies each claim against real market data stored in Pinecone. Returns a structured verdict: Verified, Misleading, False, or Unverifiable — with evidence.

---

## Architecture

<img width="1264" height="901" alt="image" src="https://github.com/user-attachments/assets/5965fa65-665d-4181-9195-fc8aa73b16b3" />


```

Data Sources
    │
    ▼
Stage 1a: Ingestion (ingestion.py)
    │  Live NSE prices via yfinance
    │  1 year historical OHLCV data
    │  ET Markets news via RSS (3 feeds)
    │  SEBI filings via RSS
    │  BSE bulk deals via CSV
    │  YouTube finfluencer transcripts
    │
    ▼
Stage 1b: Preprocessing (preprocessing.py)
    │  Financial keyword filter
    │  TTL expiry check
    │  Hash-based deduplication
    │
    ▼
Stage 1c: Chunking (chunker.py)
    │  Source-specific chunk sizes
    │  RecursiveCharacterTextSplitter
    │
    ▼
Stage 2: Embedding + Vector Store (embedder.py)
    │  BAAI/bge-base-en-v1.5 (768 dims)
    │  Pinecone (cloud, shared team access)
    │  Chroma (local dev fallback)
    │
    ▼
Stage 3: RAG Service (rag_service.py)
    │  MMR retrieval (k=5, fetch_k=20)
    │  Mode-specific prompt augmentation
    │  Groq LLM (llama-3.1-70b-versatile)
    │
    ▼
FastAPI Backend (main.py)
    │  POST /api/chat
    │  POST /api/radar
    │  POST /api/factcheck
    │
    ▼
React / Next.js Frontend
```

The pipeline runs daily via `scheduler.py` (or manually) to keep the vector store fresh. FastAPI loads the retriever once on startup and serves all user requests from the same in-memory connection.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| LLM Inference | Groq (llama-3.1-70b-versatile) |
| Embedding Model | BAAI/bge-base-en-v1.5 (HuggingFace) |
| Vector Store (cloud) | Pinecone (serverless, cosine, 768 dims) |
| Vector Store (local) | Chroma (disk-persisted) |
| RAG Framework | LangChain |
| API Framework | FastAPI + Uvicorn |
| Data Sources | yfinance, feedparser, YouTube Transcript API |
| Scheduler | Python schedule library |
| Frontend | React / Next.js (separate repo) |

---

## Project Structure

```
marketmind/
├── backend/
│   ├── main.py                          # FastAPI entry point
│   ├── requirements.txt                 # All Python dependencies
│   ├── .env.template                    # Environment variable template
│   ├── scheduler.py                     # Daily pipeline scheduler
│   ├── verify_setup.py                  # Setup verification script
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py                      # POST /api/chat
│   │   ├── radar.py                     # POST /api/radar
│   │   └── factcheck.py                 # POST /api/factcheck
│   └── rag_pipeline/
│       ├── __init__.py
│       ├── pipeline_runner.py           # Full pipeline orchestrator
│       ├── rag_service.py               # RAG core: retrieval + generation
│       ├── stage1_ingestion/
│       │   ├── __init__.py
│       │   ├── ingestion.py             # Data loaders (5 sources)
│       │   ├── preprocessing.py         # Cleaning, TTL, deduplication
│       │   └── chunker.py               # Source-specific text splitting
│       └── stage2_embedding/
│           ├── __init__.py
│           └── embedder.py              # BGE embeddings + vector store
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A drive with at least 1 GB free space (for the BGE model cache)
- A Pinecone account (free tier is sufficient)
- A Groq account (free tier is sufficient)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/marketmind.git
cd marketmind
```

### 2. Create and activate a virtual environment

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
cd backend
pip install -r requirements.txt
pip install yfinance html5lib lxml
```

### 4. Configure environment variables

```bash
copy .env.template .env      # Windows
cp .env.template .env        # macOS / Linux
```

Open `.env` and fill in all required values. See [Environment Variables](#environment-variables) for the full list.

### 5. Verify setup

```bash
python verify_setup.py
```

This script checks all dependencies, downloads the BGE model on first run (~438 MB, one-time), verifies your Pinecone connection, and confirms Groq is responding. Run it iteratively — if it reports missing packages, install them and run again until all checks pass.

---

## Environment Variables

Create a `.env` file in the `backend/` directory using `.env.template` as a guide. Never commit your `.env` file to version control.

| Variable | Description | Example |
|---|---|---|
| `PINECONE_API_KEY` | Pinecone API key | `pc-abc123...` |
| `PINECONE_INDEX` | Pinecone index name | `marketmind` |
| `GROQ_API_KEY` | Groq API key | `gsk_abc123...` |
| `GROQ_MODEL` | Groq model identifier | `llama-3.1-70b-versatile` |
| `VECTOR_STORE` | Active vector store | `pinecone` or `chroma` |
| `EMBEDDING_MODEL` | HuggingFace model name | `BAAI/bge-base-en-v1.5` |
| `CHROMA_PERSIST_DIR` | Local Chroma DB path | `./chroma_db` |
| `HF_HOME` | HuggingFace model cache directory | `D:\marketmind\hf_cache` |

**Pinecone index configuration:**

```
Name:      marketmind
Dimension: 768
Metric:    cosine
Cloud:     aws
Region:    us-east-1
```

---

## Running the Pipeline

The pipeline ingests all data sources, cleans and chunks the documents, embeds them, and upserts them into Pinecone.

### First run (loads 1 year of historical price data)

Open `backend/rag_pipeline/pipeline_runner.py` and set `force_historical=True` in the `__main__` block. Then run:

```bash
cd backend
python -m rag_pipeline.pipeline_runner
```

This takes approximately 8-12 minutes on the first run. After it completes, set `force_historical=False` immediately — you do not want to re-download historical data on every subsequent run.

### Daily runs

```bash
cd backend
python -m rag_pipeline.pipeline_runner
```

Each daily run fetches fresh prices, news, and SEBI filings. Takes approximately 2-3 minutes. Historical data is skipped automatically after the first run.

### Automated daily scheduling

To run the pipeline automatically every morning at 8 AM, start the scheduler in a separate terminal and keep it running:

```bash
cd backend
python scheduler.py
```

The scheduler uses the Python `schedule` library and triggers the full pipeline daily. Start this only after Stage 3 is verified working.

---

## Running the API Server

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On startup, FastAPI calls `init_rag()` which loads the BGE embedding model and connects to Pinecone. This takes approximately 10-15 seconds. Once running, all endpoints are available at `http://localhost:8000`.

Verify the server is healthy:
```
GET http://localhost:8000/health
```

Interactive API documentation is available at:
```
http://localhost:8000/docs
```

---

## API Reference

### POST /api/chat

General market Q&A powered by RAG.

**Request:**
```json
{
  "query": "What is the current price of Reliance and its recent trend?",
  "history": []
}
```

**Response:**
```json
{
  "answer": "Reliance Industries (RELIANCE) is currently trading at ₹1,407.80...",
  "sources": [
    {
      "chunk_id": 1,
      "source": "yfinance_live",
      "type": "price",
      "ticker": "RELIANCE",
      "date": "2026-03-25"
    }
  ],
  "confidence": "high",
  "intent": "stock_analysis",
  "meta": {
    "processing_time": "1.8s",
    "model": "Llama-3.1-70B",
    "chunks_retrieved": 5
  }
}
```

---

### POST /api/radar

Surfaces investment opportunities from the vector store.

**Request:**
```json
{
  "query": "Show me stocks with unusual bulk deal activity"
}
```

**Response:**
```json
{
  "answer": "1. **HDFCBANK** - Institutional Accumulation\n   Key Data: FII stake at 52-week high...",
  "sources": [...],
  "meta": {
    "processing_time": "2.1s",
    "model": "Llama-3.1-70B",
    "chunks_retrieved": 10
  }
}
```

---

### POST /api/factcheck

Verifies claims from a YouTube finfluencer video.

**Request:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response:**
```json
{
  "claims": [
    {
      "claim": "Finfluencer claim from video",
      "verdict": "misleading",
      "explanation": "The claim that Reliance will hit ₹4000 by next month...",
      "source": "MarketMind RAG — Pinecone index"
    }
  ],
  "summary": {
    "verified": 0,
    "misleading": 1,
    "false": 0,
    "unverifiable": 0
  },
  "raw_answer": "...",
  "meta": {
    "processing_time": "6.4s",
    "transcript_chunks": 4,
    "clean_chunks": 3,
    "model": "Llama-3.1-70B"
  }
}
```

---

### Error Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Bad request — invalid query or URL |
| 429 | Rate limit exceeded — wait 60 seconds |
| 500 | Server error — check logs |

---

## Data Sources

| Source | Type | Frequency | TTL |
|---|---|---|---|
| NSE via yfinance | Live stock prices (49 Nifty50 stocks) | Daily | 1 day |
| yfinance historical | 1 year OHLCV data (49 stocks) | Once | Permanent |
| ET Markets RSS | News articles (stocks, markets, economy) | Daily | 7 days |
| SEBI RSS | Circulars, orders, press releases | Daily | 7 days |
| BSE bulk deals | Institutional deal activity | Manual CSV | 30 days |
| YouTube | Finfluencer video transcripts | On demand | 90 days |

TTL controls how long each document type remains active in retrieval. Expired documents stay in Pinecone but are filtered at query time. At a rate of approximately 100-200 new chunks per day, the Pinecone free tier (100k vectors) provides over 2 years of runway.

---

## Pipeline Design

### Chunking Strategy

Different data types have different information density and are chunked accordingly:

| Type | Chunk Size | Overlap | Rationale |
|---|---|---|---|
| Price data | No split | — | Each stock price is one atomic fact |
| Bulk deals | No split | — | Each deal is one structured record |
| News articles | 500 chars | 80 chars | Paragraphs need cross-sentence context |
| SEBI filings | 400 chars | 60 chars | Dense legal text needs precise retrieval |
| YouTube transcripts | 300 chars | 50 chars | Spoken language is less dense |

### Embedding Model

BAAI/bge-base-en-v1.5 was chosen over all-MiniLM-L6-v2 for this use case because it scores significantly higher on financial retrieval benchmarks (MTEB score 63.5 vs 56.2) and handles Indian financial terminology, ticker symbols, and SEBI regulatory language more accurately. It runs on CPU with 768-dimensional embeddings and requires `normalize_embeddings=True` for correct cosine similarity.

### Retrieval

MMR (Maximum Marginal Relevance) is used instead of standard similarity search to prevent the retriever from returning five near-identical chunks from the same source. MMR balances relevance (lambda=0.6) with diversity across sources, ensuring answers draw from multiple data types.


---

## Known Limitations

**TATAMOTORS.NS** returns a 404 from Yahoo Finance. This is a Yahoo Finance data issue unrelated to the codebase. The ticker is skipped gracefully.

**SEBI RSS** sometimes returns empty feeds. This is expected — the feed only contains entries when SEBI publishes new items. It auto-populates when filings are released.

**BSE bulk deals** cannot be scraped automatically as BSE blocks programmatic access. Download the CSV manually from `bseindia.com` and place it at `backend/data/bse_bulk_deals.csv` to include bulk deal data.

**YouTube transcripts** require videos with captions enabled. Videos without auto-generated or manual captions will return no data. Verify a video has transcripts by checking the three-dot menu below the video on YouTube before adding its URL.

**File attachments** (PDF analysis via chat) are not implemented in the current version. The frontend API spec includes this as a future enhancement.

---

## Roadmap

- Add FinBERT sentiment scoring to the Opportunity Radar for per-stock sentiment labels
- Implement NSE historical bulk deal scraping to replace the manual BSE CSV workflow
- Add PDF document ingestion via the chat attachment field
- Expand ET Markets RSS coverage to IPO, mutual funds, and commodities feeds
- Add automatic finfluencer channel monitoring for new video detection
- Migrate from CPU inference to GPU for faster embedding on large pipeline runs
- Add a caching layer (Redis) for repeated queries to reduce Groq API calls

---

## License

All data accessed through third-party APIs (yfinance, ET Markets RSS, SEBI RSS, YouTube) is subject to the respective terms of service of those providers.
