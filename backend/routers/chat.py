"""
MarketMind AI — Chat Router
POST /api/chat — RAG-powered market Q&A
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
import re

from rag_pipeline.rag_service import generate_answer

router = APIRouter()


class HistoryItem(BaseModel):
    role: str
    content: str
    timestamp: Optional[int] = None
    attachments: Optional[List] = []


class Attachment(BaseModel):
    url: str
    name: str
    mimeType: str


class ChatRequest(BaseModel):
    query: str
    history: Optional[List[HistoryItem]] = []
    attachments: Optional[List[Attachment]] = []


class IntelligenceContext(BaseModel):
    ticker: Optional[str] = None
    price: Optional[str] = None
    change: Optional[str] = None
    up: Optional[bool] = None
    volume: Optional[str] = None
    sentiment: Optional[float] = None
    sentimentLabel: Optional[str] = None


class NewsItem(BaseModel):
    headline: str
    source: str
    time: str
    sentiment: str
    url: str


class Insight(BaseModel):
    text: str
    type: str  # "positive", "negative", "neutral"


class Intelligence(BaseModel):
    context: Optional[IntelligenceContext] = None
    news: Optional[List[NewsItem]] = []
    insights: Optional[List[Insight]] = []


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: str
    intent: str
    intelligence: Optional[Intelligence] = None
    meta: Dict[str, Any]


def extract_intelligence(answer: str, sources: list) -> Intelligence:
    """
    Extract structured intelligence from LLM answer and sources.
    This parses ticker, price, sentiment from the RAG response.
    """
    # Extract ticker from answer or sources
    ticker = None
    price = None
    change = None
    
    # sources is a list of dicts with 'source', 'type', 'ticker', etc.
    for src in sources:
        if isinstance(src, dict):
            if 'ticker' in src and src['ticker']:
                ticker = src['ticker']
                break
        elif isinstance(src, str):
            ticker_match = re.search(r'\| ([A-Z]+) \|', src)
            if ticker_match:
                ticker = ticker_match.group(1)
                break
    
    # Try to extract price and change from answer
    price_match = re.search(r'₹([\d,]+\.?\d*)', answer)
    if price_match:
        price = f"₹{price_match.group(1)}"
    
    change_match = re.search(r'([+-]?\d+\.?\d*)%', answer)
    if change_match:
        change = f"{change_match.group(1)}%"
    
    # Determine sentiment from answer tone
    sentiment_score = 0.5
    sentiment_label = "Neutral"
    
    bullish_words = ["bullish", "positive", "growth", "upside", "strong", "rally"]
    bearish_words = ["bearish", "negative", "decline", "downside", "weak", "fall"]
    
    answer_lower = answer.lower()
    bullish_count = sum(1 for word in bullish_words if word in answer_lower)
    bearish_count = sum(1 for word in bearish_words if word in answer_lower)
    
    if bullish_count > bearish_count:
        sentiment_score = 0.7 + (bullish_count * 0.05)
        sentiment_label = "Bullish" if sentiment_score < 0.85 else "Strongly Bullish"
    elif bearish_count > bullish_count:
        sentiment_score = 0.3 - (bearish_count * 0.05)
        sentiment_label = "Bearish" if sentiment_score > 0.15 else "Strongly Bearish"
    
    context = IntelligenceContext(
        ticker=ticker,
        price=price,
        change=change,
        up=(change and change.startswith("+")) if change else None,
        volume=None,
        sentiment=min(max(sentiment_score, 0), 1),
        sentimentLabel=sentiment_label
    )
    
    # Extract insights from answer
    insights = []
    sentences = answer.split(". ")
    for sentence in sentences[:3]:
        if len(sentence) > 20:
            insight_type = "positive" if any(w in sentence.lower() for w in bullish_words) else "neutral"
            if any(w in sentence.lower() for w in bearish_words):
                insight_type = "negative"
            insights.append(Insight(text=sentence.strip(), type=insight_type))
    
    return Intelligence(
        context=context,
        news=[],
        insights=insights
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.query or len(request.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if request.attachments:
        print(f"[WARN] Attachments received but not processed in MVP: {len(request.attachments)} files")
    
    start = time.time()
    
    try:
        result = generate_answer(request.query, mode="chat")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    duration = round(time.time() - start, 2)
    
    # Extract intelligence from answer
    intelligence = extract_intelligence(result["answer"], result["sources"])
    
    # Format sources as strings for frontend
    formatted_sources = []
    for src in result["sources"]:
        if isinstance(src, dict):
            formatted_sources.append(
                f"{src.get('type', 'unknown')} | {src.get('ticker', 'N/A')} | "
                f"{src.get('date', 'N/A')} | {src.get('source', 'N/A')}"
            )
        else:
            formatted_sources.append(str(src))
    
    return ChatResponse(
        answer=result["answer"],
        sources=formatted_sources,
        confidence="high" if result["chunks"] >= 3 else "medium",
        intent="stock_analysis",
        intelligence=intelligence,
        meta={
            "processing_time": f"{duration}s",
            "model": "Llama-3.3-70B",
            "chunks_retrieved": result["chunks"],
        }
    )