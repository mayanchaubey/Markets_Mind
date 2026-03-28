<div align="center">

# MarketMind AI

**RAG-powered Indian stock market intelligence**  
Real-time analysis · Opportunity detection · Finfluencer fact-checking

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-latest-1C3C3C?style=flat-square)](https://langchain.com)
[![Pinecone](https://img.shields.io/badge/Pinecone-Cloud-6B4FBB?style=flat-square)](https://pinecone.io)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=flat-square)](https://groq.com)

</div>

---

## Table of Contents


- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Data Sources](#data-sources)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)

---
## What is MarketMind AI?

MarketMind AI is a Retrieval-Augmented Generation (RAG) system built for Indian equity market intelligence. Every answer it gives is grounded in real, retrieved data — not hallucinated knowledge.

The system ingests live NSE prices, ET Markets news, SEBI filings, BSE bulk deals, and YouTube finfluencer transcripts daily. It embeds this data into a shared Pinecone vector store and serves expert-level responses through a FastAPI backend connected to Groq's fast LLM inference.

**Built for a hackathon. Structured to become a product.**

---

## Features

### 💬 Market Chat
Ask questions in plain English — *"What is the FII activity this week?"* or *"Analyse HDFC Bank's recent movement."* — and get answers grounded in retrieved market data with cited sources. General questions go directly to the LLM; stock-specific queries route through Pinecone retrieval first.

### 📡 Opportunity Radar
Scans the vector store for investment signals: unusual bulk deals, stocks near 52-week highs, strong price momentum, and positive regulatory filings. Returns the top 5–10 opportunities with ticker, signal type, key data points, and rationale.

### ✅ Finfluencer Fact-Checker
Paste any YouTube URL. The system fetches the full transcript, extracts financial claims chunk by chunk, and verifies each claim against real market data in Pinecone. Returns a structured verdict — **Verified**, **Misleading**, **False**, or **Unverifiable** — with evidence and a video-level risk score.

---

## Architecture

<img width="1264" height="901" alt="image" src="https://github.com/user-attachments/assets/5965fa65-665d-4181-9195-fc8aa73b16b3" />

```
Data Sources
    │
    ├── yfinance (live NSE prices + 1yr OHLCV history)
    ├── ET Markets RSS (3 news feeds, ~100 articles/day)
    ├── SEBI RSS (filings, circulars, orders)
    ├── BSE bulk deals (manual CSV)
    └── YouTube Transcript API (finfluencer videos)
    │
    ▼
Stage 1 — Ingestion & Preprocessing
    │  ingestion.py    → load all sources into LangChain Documents
    │  preprocessing.py → financial keyword filter, TTL expiry, hash dedup
    │  chunker.py      → source-specific chunk sizes
    │
    ▼
Stage 2 — Embedding & Vector Store
    │  BAAI/bge-base-en-v1.5 (768 dims, normalize=True)
    │  Pinecone (cloud, shared team) ← production
    │  Chroma (local disk)           ← development
    │
    ▼
Stage 3 — RAG Service
    │  Smart query routing (RAG vs direct LLM)
    │  MMR retrieval (k=5, fetch_k=20, λ=0.6)
    │  Mode-specific prompt augmentation
    │  Groq — llama-3.3-70b-versatile
    │  In-memory response cache (5 min TTL)
    │
    ▼
FastAPI Backend
    │  POST /api/chat
    │  POST /api/radar
    │  POST /api/factcheck
    │  GET  /api/dashboard/summary
    │  GET  /api/landing/data
    │  POST /api/upload-url
    │
    ▼
React / Next.js Frontend
```

The pipeline runs daily via `scheduler.py` and keeps the vector store fresh. FastAPI loads the BGE model and Pinecone retriever once on startup — all requests reuse the same in-memory connection.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| LLM | Groq · llama-3.3-70b-versatile |
| Embeddings | BAAI/bge-base-en-v1.5 (HuggingFace) |
| Vector Store | Pinecone (cloud) · Chroma (local dev) |
| RAG Framework | LangChain |
| API | FastAPI + Uvicorn |
| Data Ingestion | yfinance · feedparser · youtube-transcript-api |
| Scheduler | Python `schedule` library |
| Frontend | React / Next.js |

---

## Project Structure

```
marketmind/
├── backend/
│   ├── main.py                        # FastAPI entry point
│   ├── requirements.txt
│   ├── .env.template
│   ├── scheduler.py                   # Daily pipeline automation
│   ├── verify_setup.py                # Pre-flight checks
│   ├── routers/
│   │   ├── chat.py                    # POST /api/chat
│   │   ├── radar.py                   # POST /api/radar
│   │   ├── factcheck.py               # POST /api/factcheck
│   │   ├── dashboard.py               # GET  /api/dashboard/summary
│   │   ├── landing.py                 # GET  /api/landing/data
│   │   └── upload.py                  # POST /api/upload-url
│   └── rag_pipeline/
│       ├── pipeline_runner.py         # Full pipeline orchestrator
│       ├── rag_service.py             # RAG core: retrieval + generation
│       ├── stage1_ingestion/
│       │   ├── ingestion.py           # Data loaders (5 sources)
│       │   ├── preprocessing.py       # Cleaning, TTL, dedup
│       │   └── chunker.py             # Text splitting
│       ├── stage2_embedding/
│       │   └── embedder.py            # BGE embeddings + vector store
│       └── factcheck_pipeline/
│           ├── orchestrator.py        # Fact-check flow coordinator
│           ├── transcript_handler.py  # YouTube + metadata fallback
│           ├── claim_extractor.py     # Groq-powered claim extraction
│           └── claim_verifier.py      # Per-claim verdict generation
└── frontend/
    └── ...                            # React / Next.js app
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- At least 1 GB free disk space (BGE model is ~438 MB)
- [Pinecone](https://pinecone.io) account (free tier)
- [Groq](https://console.groq.com) account (free tier)

### 1. Clone and set up environment

```bash
git clone https://github.com/your-org/marketmind.git
cd marketmind/backend

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
pip install yfinance html5lib lxml
```

### 2. Configure environment variables

```bash
# Windows
copy .env.template .env

# macOS / Linux
cp .env.template .env
```

Fill in your `.env` file — see the [Environment Variables](#environment-variables) section below.

### 3. Run setup verification

```bash
python verify_setup.py
```

This checks all dependencies, downloads the BGE model on first run (~5 min, one-time), verifies your Pinecone connection, and confirms Groq is responding. Run it iteratively until all checks pass.

### 4. Run the pipeline (first time only)

Open `rag_pipeline/pipeline_runner.py`, set `force_historical=True` in the `__main__` block, then run:

```bash
python -m rag_pipeline.pipeline_runner
```

This loads 1 year of historical OHLCV data. Takes 8–12 minutes. After it completes, **immediately set `force_historical=False`** — you don't want to re-download history on every daily run.

### 5. Start the API server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's running: `GET http://localhost:8000/health`  
Interactive API docs: `http://localhost:8000/docs`

### 6. Start the frontend

```bash
cd ../frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `PINECONE_API_KEY` | Pinecone API key | `pc-abc123...` |
| `PINECONE_INDEX` | Index name | `marketmind` |
| `GROQ_API_KEY` | Groq API key | `gsk_abc123...` |
| `GROQ_MODEL` | Model identifier | `llama-3.3-70b-versatile` |
| `VECTOR_STORE` | Active store | `pinecone` or `chroma` |
| `EMBEDDING_MODEL` | HuggingFace model | `BAAI/bge-base-en-v1.5` |
| `CHROMA_PERSIST_DIR` | Local Chroma path | `./chroma_db` |
| `HF_HOME` | Model cache directory | `D:\marketmind\hf_cache` |

**Pinecone index settings:**
```
Name:      marketmind
Dimension: 768
Metric:    cosine
Cloud:     aws / Region: us-east-1
```

> ⚠️ Never commit your `.env` file. It's in `.gitignore` by default.

---

## Daily Pipeline

Run manually any time to refresh the vector store:

```bash
cd backend
python -m rag_pipeline.pipeline_runner
```

Each daily run fetches fresh prices, news, and SEBI filings (~2–3 minutes). Historical data is skipped automatically after the first run.

To automate at 08:00 AM daily, start the scheduler in a separate terminal:

```bash
python scheduler.py
```

Keep this terminal open. It runs the pipeline every morning and logs results. Start it after verifying the full system works end to end.

---

## API Reference

### POST `/api/chat`

```json
// Request
{ "query": "What is the FII activity this week?", "history": [] }

// Response
{
  "answer": "FIIs sold ₹3,200 Cr net this week, primarily in banking...",
  "sources": ["price | HDFCBANK | 2026-03-25 | yfinance_live"],
  "confidence": "high",
  "intent": "stock_analysis",
  "meta": { "processing_time": "1.8s", "chunks_retrieved": 5 }
}
```

### POST `/api/radar`

```json
// Request
{ "query": "Stocks with unusual bulk deal activity" }

// Response — array of opportunity signals
[
  {
    "ticker": "BAJFINANCE",
    "signal_type": "BULLISH",
    "description": "Strong 4.61% day change indicating upward momentum",
    "finbert_score": 0.82,
    "source": "NSE",
    "timestamp": "2026-03-29T08:15:00Z"
  }
]
```

### POST `/api/factcheck`

```json
// Request
{ "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID" }

// Response
{
  "claims": [
    {
      "claim": "Reliance will hit ₹4000 by next month",
      "verdict": "false",
      "explanation": "Current price is ₹1,411. 52W high is ₹1,611. No data supports a ₹4000 target.",
      "source": "MarketMind RAG",
      "confidence": 0.91
    }
  ],
  "summary": { "verified": 0, "misleading": 0, "false": 1, "unverifiable": 0 },
  "risk_score": 0.72,
  "risk_label": "High Risk",
  "processing_time": 10.8
}
```

| Code | Meaning |
|---|---|
| `200` | Success |
| `400` | Invalid query or URL |
| `429` | Groq rate limit — wait 60 seconds |
| `500` | Server error — check logs |

---

## Data Sources

| Source | Data Type | Frequency | TTL |
|---|---|---|---|
| yfinance (live) | NSE prices, 49 Nifty50 stocks | Daily | 1 day |
| yfinance (historical) | 1 year OHLCV per stock | Once | Permanent |
| ET Markets RSS | News (stocks, markets, economy) | Daily | 7 days |
| SEBI RSS | Circulars, orders, press releases | Daily | 7 days |
| BSE bulk deals | Institutional deal activity | Manual CSV | 30 days |
| YouTube | Finfluencer transcripts | On demand | 90 days |

At ~100–200 new chunks per day, the Pinecone free tier (100k vectors) gives over 2 years of runway.

---

## Design Decisions

**Why BAAI/bge-base-en-v1.5 over all-MiniLM-L6-v2?**  
BGE scores higher on financial retrieval benchmarks (MTEB 63.5 vs 56.2) and handles Indian financial terminology, NSE tickers, and SEBI regulatory language more accurately. Requires `normalize_embeddings=True`.

**Why MMR over standard similarity search?**  
MMR (Maximum Marginal Relevance) prevents returning five near-identical chunks from the same source. With λ=0.6, it balances relevance with diversity across data types — ensuring chat answers draw from prices, news, and filings together rather than repeating the same document.

**Why smart query routing?**  
Not every question needs Pinecone. General questions like *"how does a P/E ratio work?"* get better answers directly from the LLM without retrieval noise. Stock-specific queries containing tickers, indices, or market terms route through Pinecone as normal.

**Why response caching?**  
The frontend fires multiple parallel radar calls on page load. Without caching, each call burns Groq tokens and triggers Pinecone retrieval. A 5-minute in-memory cache returns stored results instantly for duplicate queries, eliminating the latency issue entirely.

---

## Known Limitations

- **TATAMOTORS.NS** returns a 404 from Yahoo Finance — a data provider issue, not a code bug. Skipped gracefully.
- **SEBI RSS** is sometimes empty. Expected — the feed only has entries when SEBI publishes. Auto-populates.
- **BSE bulk deals** require manual CSV download from `bseindia.com` — BSE blocks automated scraping.
- **YouTube transcripts** require captions to be enabled. Verify via the three-dot menu below any video.
- **File attachments** (PDF chat analysis) are in the API spec but not yet implemented.

---

## Roadmap

- FinBERT sentiment scoring per stock on the Opportunity Radar
- Automated finfluencer channel monitoring for new video detection  
- PDF document ingestion via chat attachments
- NSE historical bulk deal scraping (replacing manual BSE CSV)
- Redis caching layer for high-traffic deployments
- GPU inference support for faster embedding on large pipeline runs

---

## License

Data accessed through yfinance, ET Markets RSS, SEBI RSS, and the YouTube Transcript API is subject to the respective terms of service of those providers. This project is built for educational and hackathon purposes.
