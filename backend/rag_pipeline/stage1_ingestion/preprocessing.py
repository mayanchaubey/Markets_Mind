"""
MarketMind AI — Stage 1: Preprocessing & Cleaning
Cleans raw Documents before they go to the chunker.
Filters out non-financial content, removes boilerplate, deduplicates.
"""

import re
import hashlib
from datetime import datetime, date
from langchain_core.documents import Document


# ─────────────────────────────────────────────
# FINANCIAL KEYWORD FILTER
# ─────────────────────────────────────────────
# This is the most important gate — drops ~60-70% of raw text
# that is irrelevant (filler, ads, generic YouTube speech, etc.)

FINANCIAL_KEYWORDS = [
    # Market entities
    "nifty", "sensex", "bse", "nse", "sebi", "ipo", "nfo",
    "fii", "dii", "bulk deal", "insider", "promoter", "operator",
    # Financial metrics
    "pe ratio", "p/e", "eps", "revenue", "profit", "loss",
    "ebitda", "debt", "equity", "market cap", "dividend", "yield",
    "quarterly", "annual report", "balance sheet", "cash flow",
    "roce", "roe", "net worth", "book value", "face value",
    # Stock actions
    "buy", "sell", "hold", "target price", "stop loss", "cagr",
    "returns", "sip", "mutual fund", "portfolio", "rally", "crash",
    "correction", "resistance", "support", "breakout", "breakdown",
    # Indian finance specific
    "crore", "lakh", "rupee", "inr", "rbi", "repo rate", "reverse repo",
    "inflation", "cpi", "wpi", "gdp", "fiscal", "budget", "gst",
    "fema", "rbi circular", "monetary policy",
    # Corporate actions
    "merger", "acquisition", "demerger", "rights issue", "bonus share",
    "stock split", "buyback", "delisting", "listing", "preferential allotment",
    # Instruments
    "stock", "share", "equity", "bond", "debenture", "futures",
    "options", "derivative", "etf", "index fund", "smallcap",
    "midcap", "largecap", "bluechip",
]


def has_financial_signal(text: str) -> bool:
    """Returns True if text contains at least one financial keyword."""
    lower = text.lower()
    return any(kw in lower for kw in FINANCIAL_KEYWORDS)


# ─────────────────────────────────────────────
# SOURCE-SPECIFIC CLEANERS
# ─────────────────────────────────────────────

BOILERPLATE_PATTERNS = [
    r"subscribe to.*?newsletter",
    r"click here to (read|watch|know) more",
    r"also read[:\s].*",
    r"also watch[:\s].*",
    r"follow us on.*",
    r"disclaimer[:\s].*",
    r"terms and conditions.*",
    r"all rights reserved.*",
    r"advertisement",
    r"this article (is|was) (first )?published.*",
    r"read more at.*",
    r"for more (info|details|updates).*",
    r"\(with inputs from.*?\)",
]

FILLER_WORDS_PATTERN = re.compile(
    r"\b(um|uh|you know|like i said|basically|right\?|okay so|"
    r"alright so|so yeah|you see|i mean|sort of|kind of|"
    r"let me tell you|guys|friends)\b",
    re.IGNORECASE,
)

TRANSCRIPT_ARTIFACTS_PATTERN = re.compile(r"\[.*?\]|\(.*?applause.*?\)")


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _remove_boilerplate(text: str) -> str:
    for pattern in BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def clean_price_document(doc: Document) -> Document | None:
    """Price data is already structured — just validate it."""
    if not doc.page_content or len(doc.page_content) < 30:
        return None
    return doc


def clean_sebi_document(doc: Document) -> Document | None:
    """Clean SEBI RSS entry."""
    text = _strip_html(doc.page_content)
    text = _normalize_whitespace(text)
    if len(text) < 60:
        return None
    if not has_financial_signal(text):
        return None
    return Document(page_content=text, metadata=doc.metadata)


def clean_bulk_deal_document(doc: Document) -> Document | None:
    """Bulk deal is structured — validate non-empty."""
    if not doc.page_content or "₹0.00" in doc.page_content:
        return None
    return doc


def clean_youtube_document(doc: Document) -> Document | None:
    """Clean YouTube transcript segment."""
    text = TRANSCRIPT_ARTIFACTS_PATTERN.sub("", doc.page_content)
    text = FILLER_WORDS_PATTERN.sub("", text)
    text = _normalize_whitespace(text)
    if len(text) < 80:
        return None
    if not has_financial_signal(text):
        return None  # <-- this alone drops ~65% of transcript noise
    return Document(page_content=text, metadata=doc.metadata)


def clean_news_document(doc: Document) -> Document | None:
    """Clean ET Markets / news article."""
    text = _strip_html(doc.page_content)
    text = _remove_boilerplate(text)
    text = _normalize_whitespace(text)
    if len(text) < 100:
        return None
    return Document(page_content=text, metadata=doc.metadata)


# ─────────────────────────────────────────────
# TTL EXPIRY CHECK
# ─────────────────────────────────────────────

def is_expired(doc: Document) -> bool:
    """
    Returns True if the document is older than its TTL.
    TTL is set per source type in metadata (ttl_days).
    """
    meta = doc.metadata
    date_str = meta.get("date") or meta.get("published")
    if not date_str:
        return False
    try:
        # Handle common date string formats
        for fmt in ("%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %z",
                    "%a, %d %b %Y %H:%M:%S GMT"):
            try:
                doc_date = datetime.strptime(str(date_str), fmt)
                break
            except ValueError:
                continue
        else:
            return False
        ttl = meta.get("ttl_days", 7)
        return (datetime.now(tz=doc_date.tzinfo) - doc_date).days > ttl
    except Exception:
        return False


# ─────────────────────────────────────────────
# DEDUPLICATION
# ─────────────────────────────────────────────

class DedupFilter:
    """
    Hash-based deduplication. Maintains a set of seen content hashes
    for the duration of a pipeline run.
    """
    def __init__(self):
        self._seen: set[str] = set()

    def is_duplicate(self, doc: Document) -> bool:
        normalized = re.sub(r"\s+", " ", doc.page_content.lower().strip())
        h = hashlib.md5(normalized.encode()).hexdigest()
        if h in self._seen:
            return True
        self._seen.add(h)
        return False

    def reset(self):
        self._seen.clear()


# ─────────────────────────────────────────────
# MASTER CLEANER
# ─────────────────────────────────────────────

CLEANER_MAP = {
    "price": clean_price_document,
    "filing": clean_sebi_document,
    "bulk_deal": clean_bulk_deal_document,
    "transcript": clean_youtube_document,
    "news": clean_news_document,
}


def run_cleaning(raw_docs: list[Document]) -> list[Document]:
    """
    Run all cleaning passes over raw Documents.
    Returns clean, deduplicated, non-expired Documents.

    Pipeline per document:
      1. Route to source-specific cleaner
      2. TTL expiry check
      3. Deduplication
    """
    dedup = DedupFilter()
    clean_docs: list[Document] = []

    stats = {
        "total_in": len(raw_docs),
        "dropped_cleaner": 0,
        "dropped_expired": 0,
        "dropped_duplicate": 0,
        "passed": 0,
    }

    for doc in raw_docs:
        doc_type = doc.metadata.get("type", "news")
        cleaner = CLEANER_MAP.get(doc_type, clean_news_document)

        # Stage 1: source-specific cleaning + financial filter
        cleaned = cleaner(doc)
        if cleaned is None:
            stats["dropped_cleaner"] += 1
            continue

        # Stage 2: TTL expiry
        if is_expired(cleaned):
            stats["dropped_expired"] += 1
            continue

        # Stage 3: deduplication
        if dedup.is_duplicate(cleaned):
            stats["dropped_duplicate"] += 1
            continue

        clean_docs.append(cleaned)
        stats["passed"] += 1

    # Summary
    print("\n[Cleaning Stats]")
    print(f"  Input:             {stats['total_in']}")
    print(f"  Dropped (filter):  {stats['dropped_cleaner']}")
    print(f"  Dropped (expired): {stats['dropped_expired']}")
    print(f"  Dropped (dedup):   {stats['dropped_duplicate']}")
    print(f"  Passed:            {stats['passed']}")

    return clean_docs


if __name__ == "__main__":
    # Quick test
    sample = [
        Document(
            page_content="SEBI Filing: Bulk deal alert. Tata Power bulk deal worth ₹42 Cr detected. Promoter buying.",
            metadata={"type": "filing", "date": str(date.today()), "ttl_days": 7}
        ),
        Document(
            page_content="Hey guys subscribe to my channel for more videos! Click here to read more.",
            metadata={"type": "transcript", "date": str(date.today()), "ttl_days": 90}
        ),
        Document(
            page_content="SEBI Filing: Bulk deal alert. Tata Power bulk deal worth ₹42 Cr detected. Promoter buying.",
            metadata={"type": "filing", "date": str(date.today()), "ttl_days": 7}
        ),  # duplicate
    ]
    cleaned = run_cleaning(sample)
    print(f"\nResult: {len(cleaned)} clean documents")
    for d in cleaned:
        print(f"  [{d.metadata['type']}] {d.page_content[:80]}")