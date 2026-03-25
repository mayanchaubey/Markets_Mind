"""
MarketMind AI — Stage 1: Document Ingestion (Overhauled)
Loads rich data from all sources into LangChain Document objects.

Changes from v1:
- Multiple ET Markets RSS feeds (stocks, economy, MF, IPO, commodities)
- 1 year historical OHLCV data via yfinance (first run only)
- jugaad-trader for BSE bulk deals + manual CSV fallback
- Better YouTube error handling
- Full Nifty50 ticker list
"""

import time
import feedparser
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, date, timedelta
from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 1. YFINANCE — Live prices + 1 year historical
# ─────────────────────────────────────────────

NIFTY50_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "HCLTECH.NS",
    "ULTRACEMCO.NS", "WIPRO.NS", "TITAN.NS", "BAJFINANCE.NS", "NESTLEIND.NS",
    "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "TATAMOTORS.NS", "ADANIENT.NS",
    "ADANIPORTS.NS", "COALINDIA.NS", "TECHM.NS", "SUNPHARMA.NS", "DRREDDY.NS",
    "CIPLA.NS", "DIVISLAB.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS",
    "TATACONSUM.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "EICHERMOT.NS", "HEROMOTOCO.NS",
    "BPCL.NS", "IOC.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS",
    "GRASIM.NS", "INDUSINDBK.NS", "UPL.NS", "SHREECEM.NS", "M&M.NS",
]


def load_live_prices(tickers: list[str] = NIFTY50_TICKERS) -> list[Document]:
    """Fetch latest price snapshot for each ticker."""
    docs = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).fast_info
            text = (
                f"Stock: {ticker.replace('.NS','')} | "
                f"Date: {date.today()} | "
                f"Price: ₹{info.last_price:.2f} | "
                f"Day change: {((info.last_price - info.previous_close) / info.previous_close * 100):.2f}% | "
                f"52W High: ₹{getattr(info, 'year_high', 0):.2f} | "
                f"52W Low: ₹{getattr(info, 'year_low', 0):.2f} | "
                f"Market cap: ₹{(getattr(info, 'market_cap', 0) or 0)/1e7:.0f} Cr"
            )
            docs.append(Document(
                page_content=text,
                metadata={
                    "source": "yfinance_live",
                    "type": "price",
                    "ticker": ticker.replace(".NS", ""),
                    "date": str(date.today()),
                    "ttl_days": 1,
                }
            ))
            time.sleep(0.2)
        except Exception as e:
            logger.warning(f"yfinance live failed for {ticker}: {e}")
    logger.info(f"[Live Prices] Loaded {len(docs)} documents")
    return docs


def load_historical_prices(
    tickers: list[str] = NIFTY50_TICKERS,
    period: str = "1y"
) -> list[Document]:
    """
    Load 1 year of daily OHLCV data.
    Groups by month — one Document per ticker per month.
    Run only on first pipeline run (load_historical=True).
    Takes ~10 minutes for full Nifty50.
    """
    docs = []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False)
            if df.empty:
                continue

            df.index = pd.to_datetime(df.index)
            df["month"] = df.index.to_period("M")

            for month, group in df.groupby("month"):
                rows = []
                for idx, row in group.iterrows():
                    try:
                        close = float(row["Close"].iloc[0]) if hasattr(row["Close"], 'iloc') else float(row["Close"])
                        volume = int(row["Volume"].iloc[0]) if hasattr(row["Volume"], 'iloc') else int(row["Volume"])
                        rows.append(f"{idx.strftime('%Y-%m-%d')}: ₹{close:.2f} vol {volume:,}")
                    except Exception:
                        continue

                if rows:
                    text = (
                        f"Historical OHLCV {ticker.replace('.NS','')} {month}: "
                        + " | ".join(rows[:22])
                    )
                    docs.append(Document(
                        page_content=text,
                        metadata={
                            "source": "yfinance_historical",
                            "type": "price_history",
                            "ticker": ticker.replace(".NS", ""),
                            "month": str(month),
                            "date": str(date.today()),
                            "ttl_days": 365,
                        }
                    ))
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"yfinance historical failed for {ticker}: {e}")

    logger.info(f"[Historical Prices] Loaded {len(docs)} monthly documents")
    return docs


# ─────────────────────────────────────────────
# 2. SEBI — Multiple RSS feeds
# ─────────────────────────────────────────────

SEBI_RSS_URLS = [
    "https://www.sebi.gov.in/sebi_data/rss/sebi_news_rss.xml",
    "https://www.sebi.gov.in/sebi_data/rss/sebi_circulars_rss.xml",
    "https://www.sebi.gov.in/sebi_data/rss/sebi_orders_rss.xml",
    "https://www.sebi.gov.in/sebi_data/rss/sebi_press_rss.xml",
]


def load_sebi_filings() -> list[Document]:
    """Parse all SEBI RSS feeds."""
    docs = []
    for url in SEBI_RSS_URLS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                text = f"SEBI Filing: {title}. {summary}"
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": "sebi_rss",
                        "type": "filing",
                        "url": entry.get("link", ""),
                        "date": entry.get("published", str(date.today())),
                        "ttl_days": 30,
                    }
                ))
        except Exception as e:
            logger.warning(f"SEBI RSS failed for {url}: {e}")
    logger.info(f"[SEBI] Loaded {len(docs)} filing documents")
    return docs


# ─────────────────────────────────────────────
# 3. ET MARKETS — 6 RSS feeds
# ─────────────────────────────────────────────

ET_RSS_FEEDS = {
    "stocks":       "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "markets":      "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "mutual_funds": "https://economictimes.indiatimes.com/mf/rssfeeds/12143882.cms",
    "economy":      "https://economictimes.indiatimes.com/economy/rssfeeds/1373380680.cms",
    "ipo":          "https://economictimes.indiatimes.com/markets/ipos/fpos/rssfeeds/6715314171.cms",
    "commodities":  "https://economictimes.indiatimes.com/markets/commodities/rssfeeds/1808152122.cms",
}


def load_et_news() -> list[Document]:
    """Load ET Markets news via 6 RSS feeds."""
    docs = []
    seen_urls = set()

    for feed_name, url in ET_RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                link = entry.get("link", "")
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()

                if not title or len(summary) < 30:
                    continue

                text = f"ET Markets [{feed_name}]: {title}. {summary}"
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": f"et_{feed_name}",
                        "type": "news",
                        "url": link,
                        "date": entry.get("published", str(date.today())),
                        "ttl_days": 7,
                        "feed": feed_name,
                    }
                ))
                count += 1
            print(f"  ET [{feed_name}]: {count} articles")
        except Exception as e:
            logger.warning(f"ET RSS failed for {feed_name}: {e}")

    logger.info(f"[ET Markets] Loaded {len(docs)} total news documents")
    return docs


# ─────────────────────────────────────────────
# 4. BSE BULK DEALS — jugaad-trader + CSV fallback
# ─────────────────────────────────────────────

def load_bse_bulk_deals(csv_path: str = None) -> list[Document]:
    """
    Load BSE bulk deals.
    Priority: manual CSV → jugaad-trader → skip

    Manual CSV: download from bseindia.com, save as backend/data/bse_bulk_deals.csv
    """
    docs = []

    if csv_path:
        try:
            df = pd.read_csv(csv_path)
            docs.extend(_parse_bulk_deal_df(df))
            logger.info(f"[BSE] Loaded {len(docs)} bulk deals from CSV")
            return docs
        except Exception as e:
            logger.warning(f"BSE CSV failed: {e}")

    try:
        from jugaad_trader.nse import NSELive
        nse = NSELive()
        deals = nse.get_bulk_deals()
        if deals:
            for deal in deals:
                text = (
                    f"BSE Bulk Deal: {deal.get('symbol','?')} | "
                    f"Type: {deal.get('buySell','?')} | "
                    f"Client: {deal.get('clientName','?')} | "
                    f"Qty: {deal.get('quantity',0):,} | "
                    f"Price: ₹{deal.get('price',0):.2f} | "
                    f"Date: {deal.get('date', date.today())}"
                )
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": "nse_bulk_deals",
                        "type": "bulk_deal",
                        "ticker": deal.get("symbol", ""),
                        "date": str(deal.get("date", date.today())),
                        "ttl_days": 30,
                    }
                ))
            logger.info(f"[BSE] Loaded {len(docs)} bulk deals via jugaad-trader")
            return docs
    except ImportError:
        logger.warning("[BSE] jugaad-trader not installed. Run: pip install jugaad-trader")
    except Exception as e:
        logger.warning(f"[BSE] jugaad-trader failed: {e}")

    logger.warning("[BSE] No bulk deals loaded. Provide CSV path or install jugaad-trader.")
    return docs


def _parse_bulk_deal_df(df: pd.DataFrame) -> list[Document]:
    docs = []
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    for _, row in df.iterrows():
        try:
            qty_col = next((c for c in df.columns if "qty" in c or "quantity" in c), None)
            price_col = next((c for c in df.columns if "price" in c), None)
            ticker_col = next((c for c in df.columns if "symbol" in c or "scrip" in c), None)
            if not all([qty_col, price_col, ticker_col]):
                continue
            qty = int(str(row.get(qty_col, 0)).replace(",", ""))
            price = float(str(row.get(price_col, 0)).replace(",", ""))
            ticker = str(row.get(ticker_col, "")).strip().upper()
            if qty == 0 or price == 0 or not ticker:
                continue
            text = (
                f"BSE Bulk Deal: {ticker} | "
                f"Qty: {qty:,} shares | "
                f"Price: ₹{price:.2f} | "
                f"Value: ₹{(qty*price)/1e7:.2f} Cr"
            )
            docs.append(Document(
                page_content=text,
                metadata={
                    "source": "bse_bulk_deals",
                    "type": "bulk_deal",
                    "ticker": ticker,
                    "date": str(date.today()),
                    "ttl_days": 30,
                }
            ))
        except Exception:
            continue
    return docs


# ─────────────────────────────────────────────
# 5. YOUTUBE — Finfluencer transcripts
# ─────────────────────────────────────────────

DEFAULT_FINFLUENCER_VIDEOS = [
    # Add real finfluencer video URLs here before running
    # Example:
    # {"url": "https://www.youtube.com/watch?v=VIDEO_ID",
    #  "title": "Top 5 stocks for 2026",
    #  "channel": "Akshat Shrivastava"},
]


def _extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.hostname in ("youtu.be",):
        return parsed.path.lstrip("/")
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        qs = parse_qs(parsed.query)
        return qs.get("v", [None])[0]
    return None


def load_youtube_transcript(
    youtube_url: str,
    video_title: str = "Unknown",
    channel_name: str = "Unknown",
) -> list[Document]:
    """Extract transcript from a YouTube video — 60 second windows."""
    docs = []
    video_id = _extract_video_id(youtube_url)
    if not video_id:
        logger.warning(f"Could not extract video ID from: {youtube_url}")
        return docs

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=["en", "hi", "en-IN"])

        window = []
        window_start = 0

        for segment in transcript:
            window.append(segment.text)
            if segment.start - window_start >= 60:
                text = " ".join(window).strip()
                if text:
                    docs.append(Document(
                        page_content=f"[{channel_name}] {video_title}: {text}",
                        metadata={
                            "source": "youtube",
                            "type": "transcript",
                            "video_id": video_id,
                            "video_title": video_title,
                            "channel": channel_name,
                            "url": youtube_url,
                            "start_sec": int(window_start),
                            "ttl_days": 90,
                        }
                    ))
                window = []
                window_start = segment.start

        if window:
            text = " ".join(window).strip()
            if text:
                docs.append(Document(
                    page_content=f"[{channel_name}] {video_title}: {text}",
                    metadata={
                        "source": "youtube",
                        "type": "transcript",
                        "video_id": video_id,
                        "video_title": video_title,
                        "channel": channel_name,
                        "url": youtube_url,
                        "start_sec": int(window_start),
                        "ttl_days": 90,
                    }
                ))
    except Exception as e:
        logger.warning(f"YouTube transcript failed for {youtube_url}: {e}")

    logger.info(f"[YouTube] Loaded {len(docs)} docs from {youtube_url}")
    return docs


# ─────────────────────────────────────────────
# MASTER INGESTION RUNNER
# ─────────────────────────────────────────────

def run_ingestion(
    youtube_videos: list[dict] = None,
    bse_csv_path: str = None,
    load_historical: bool = False,
) -> list[Document]:
    """
    Run all loaders. Returns combined raw Document list.

    Args:
        youtube_videos:  list of {"url", "title", "channel"}
        bse_csv_path:    path to BSE bulk deals CSV
        load_historical: True on first run to load 1yr price history (~10 min)
                         False on daily runs (just loads today's live prices)
    """
    all_docs: list[Document] = []

    all_docs.extend(load_live_prices())
    all_docs.extend(load_sebi_filings())
    all_docs.extend(load_bse_bulk_deals(csv_path=bse_csv_path))
    all_docs.extend(load_et_news())

    if load_historical:
        print("[Historical] Loading 1 year OHLCV — takes ~10 min, only needed once...")
        all_docs.extend(load_historical_prices())

    videos = youtube_videos or DEFAULT_FINFLUENCER_VIDEOS
    for video in videos:
        all_docs.extend(load_youtube_transcript(
            youtube_url=video["url"],
            video_title=video.get("title", "Unknown"),
            channel_name=video.get("channel", "Unknown"),
        ))

    print(f"\n[Ingestion complete] Total raw documents: {len(all_docs)}")
    return all_docs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Set load_historical=True only on first run
    docs = run_ingestion(load_historical=False)
    for d in docs[:3]:
        print(d.page_content[:120])
        print(d.metadata)
        print("---")