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
    finbert_score: float  # Renamed from confidence_score per API spec
    source: str
    timestamp: str


def parse_radar_answer(answer: str, sources: list) -> List[OpportunitySignal]:
    """
    Parse LLM radar answer into structured array of opportunities.
    The LLM returns numbered list format, we convert to array.
    """
    opportunities = []
    
    # Split answer by numbered items (1., 2., 3., etc.)
    items = re.split(r'\n\d+\.\s+', answer)
    
    for item in items[1:]:  # Skip first empty split
        lines = item.strip().split('\n')
        if len(lines) < 2:
            continue
        
        # Extract ticker from first line (e.g., "**RELIANCE (RELIANCE)**")
        ticker_match = re.search(r'\*\*([A-Z]+)', lines[0])
        ticker = ticker_match.group(1) if ticker_match else "UNKNOWN"
        
        # Extract signal type from first line or description
        signal_type = "NEUTRAL"
        if "bullish" in item.lower() or "buy" in item.lower():
            signal_type = "BULLISH"
        elif "bearish" in item.lower() or "sell" in item.lower():
            signal_type = "BEARISH"
        
        # Extract description (combine all lines after first)
        description = " ".join(lines[1:]).strip()
        
        # Calculate finbert_score (0-1) based on keywords
        score = 0.5
        if signal_type == "BULLISH":
            score = 0.7 + (item.lower().count("strong") * 0.05)
        elif signal_type == "BEARISH":
            score = 0.3 - (item.lower().count("weak") * 0.05)
        score = min(max(score, 0), 1)
        
        # Extract source from metadata
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
        
        opportunities.append(OpportunitySignal(
            ticker=ticker,
            signal_type=signal_type,
            description=description[:200],  # Limit to 200 chars
            finbert_score=round(score, 2),
            source=source,
            timestamp="2026-03-26T12:00:00Z"  # Would use actual time in production
        ))
    
    return opportunities


@router.post("/radar", response_model=List[OpportunitySignal])
async def radar(request: RadarRequest):
    query = request.query or "What are today's top investment opportunities in the Indian stock market?"
    start = time.time()
    
    try:
        result = generate_answer(query, mode="radar", k=10)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Parse answer into structured array
    opportunities = parse_radar_answer(result["answer"], result["sources"])
    
    # If parsing failed, return empty array rather than crash
    if not opportunities:
        print(f"[WARN] Radar parsing failed, returning empty array")
        opportunities = []
    
    return opportunities