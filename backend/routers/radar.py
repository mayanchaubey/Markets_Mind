"""
MarketMind AI — Opportunity Radar Router
POST /api/radar — surfaces investment signals
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import time
import re

from rag_pipeline.rag_service import generate_answer

router = APIRouter()


class RadarRequest(BaseModel):
    query: Optional[str] = ""


class OpportunitySignal(BaseModel):
    ticker: str
    signal_type: str  # "BULLISH", "BEARISH", "NEUTRAL"
    description: str
    finbert_score: float
    source: str
    timestamp: str


# 🔧 IMPROVED PARSER (robust)
def parse_radar_answer(answer: str, sources: list) -> List[OpportunitySignal]:
    opportunities = []

    # Split supports multiple formats (1., -, •)
    items = re.split(r'\n\d+\.\s+|\n-\s+|\n•\s+', answer)

    print("\n📦 RAW LLM ANSWER:\n", answer)
    print("🔍 SPLIT ITEMS COUNT:", len(items))

    for item in items:
        item = item.strip()
        if len(item) < 20:
            continue

        lines = item.split('\n')

        # 🔍 Extract ticker
        ticker_match = re.search(r'\b[A-Z]{2,}\b', lines[0])
        ticker = ticker_match.group(0) if ticker_match else "UNKNOWN"

        # 🔍 Detect signal type
        lowered = item.lower()
        if "bullish" in lowered or "buy" in lowered or "uptrend" in lowered:
            signal_type = "BULLISH"
        elif "bearish" in lowered or "sell" in lowered or "downtrend" in lowered:
            signal_type = "BEARISH"
        else:
            signal_type = "NEUTRAL"

        # 🔍 Description
        description = " ".join(lines[1:]).strip()[:200]

        # 🔍 Score logic (improved variation)
        if signal_type == "BULLISH":
            score = 0.65 + min(lowered.count("strong") * 0.05, 0.2)
        elif signal_type == "BEARISH":
            score = 0.35 - min(lowered.count("weak") * 0.05, 0.2)
        else:
            score = 0.5

        score = round(min(max(score, 0), 1), 2)

        # 🔍 Source detection
        source = "MarketMind AI"
        for src in sources:
            if ticker in src:
                if "yfinance" in src:
                    source = "NSE"
                elif "et_" in src:
                    source = "ET Markets"
                elif "sebi" in src:
                    source = "SEBI"
                break

        opportunities.append(
            OpportunitySignal(
                ticker=ticker,
                signal_type=signal_type,
                description=description,
                finbert_score=score,
                source=source,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        )

    print("✅ FINAL SIGNAL COUNT:", len(opportunities))
    return opportunities


@router.post("/radar", response_model=List[OpportunitySignal])
async def radar(request: RadarRequest):
    start = time.time()

    # 🔥 STRONG PROMPT (forces multiple outputs)
    query = request.query or (
        "Give at least 8-10 Indian stock market opportunities. "
        "Strictly follow this format:\n"
        "1. TICKER - BULLISH/BEARISH/NEUTRAL\n"
        "Reason: explanation\n"
        "2. TICKER - ...\n"
        "Include mix of bullish, bearish and neutral signals."
    )

    try:
        result = generate_answer(query, mode="radar", k=15)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    opportunities = parse_radar_answer(result["answer"], result["sources"])

    # 🛑 fallback if parsing fails
    if not opportunities:
        print("[WARN] No opportunities parsed from LLM response")
        return []

    print(f"⏱ Radar completed in {round(time.time() - start, 2)}s")

    return opportunities