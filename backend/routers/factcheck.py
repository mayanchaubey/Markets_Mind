"""
MarketMind AI — Finfluencer Fact-Checker Router
POST /api/factcheck — verifies YouTube video claims
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import time
import re

from rag_pipeline.rag_service import generate_answer
from rag_pipeline.stage1_ingestion.ingestion import load_youtube_transcript
from rag_pipeline.stage1_ingestion.preprocessing import run_cleaning

router = APIRouter()


class FactCheckRequest(BaseModel):
    youtube_url: str


class Claim(BaseModel):
    claim: str
    verdict: str  # "verified", "misleading", "false", "unverifiable"
    explanation: str
    source: str


class FactCheckResponse(BaseModel):
    claims: List[Claim]
    summary: Dict[str, int]


def extract_claims_from_answer(answer: str) -> List[Claim]:
    """
    Parse LLM factcheck answer into structured claims.
    The LLM returns verdict + explanation format.
    """
    # Determine verdict from answer
    verdict = "unverifiable"
    answer_upper = answer.upper()
    
    if "VERIFIED" in answer_upper and "FALSE" not in answer_upper:
        verdict = "verified"
    elif "MISLEADING" in answer_upper:
        verdict = "misleading"
    elif "FALSE" in answer_upper:
        verdict = "false"
    
    # Extract explanation (text after "EXPLANATION:")
    explanation = answer
    if "EXPLANATION:" in answer_upper:
        idx = answer_upper.find("EXPLANATION:")
        explanation = answer[idx + len("EXPLANATION:"):].strip()
    
    # Extract claim from explanation if possible
    claim_text = "Finfluencer claim from video"
    sentences = explanation.split(". ")
    if sentences:
        # First sentence often contains the claim
        claim_text = sentences[0][:100]  # First 100 chars
    
    return [Claim(
        claim=claim_text,
        verdict=verdict,
        explanation=explanation[:500],  # Limit to 500 chars
        source="MarketMind RAG — Pinecone index"
    )]


@router.post("/factcheck", response_model=FactCheckResponse)
async def factcheck(request: FactCheckRequest):
    url = request.youtube_url.strip()
    if not url or ("youtube.com" not in url and "youtu.be" not in url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    start = time.time()
    
    # Step 1 — Fetch transcript from the video
    try:
        transcript_docs = load_youtube_transcript(
            youtube_url=url,
            video_title="Finfluencer Video",
            channel_name="Unknown",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch transcript: {str(e)}"
        )
    
    if not transcript_docs:
        raise HTTPException(
            status_code=400,
            detail="No transcript found. Video may not have captions enabled."
        )
    
    # Step 2 — Clean the transcript
    clean_docs = run_cleaning(transcript_docs)
    if not clean_docs:
        raise HTTPException(
            status_code=400,
            detail="Transcript did not pass financial content filter. Video may not contain market-related content."
        )
    
    # Step 3 — Build query from transcript content
    combined_text = " ".join([d.page_content for d in clean_docs[:5]])
    query = f"Verify these claims from a finfluencer video: {combined_text[:800]}"
    
    # Step 4 — Run factcheck against Pinecone
    try:
        result = generate_answer(query, mode="factcheck")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Step 5 — Parse answer into structured claims
    claims = extract_claims_from_answer(result["answer"])
    
    # Step 6 — Build summary counts
    summary = {"verified": 0, "misleading": 0, "false": 0, "unverifiable": 0}
    for claim in claims:
        v = claim.verdict.lower()
        if v in summary:
            summary[v] += 1
    
    return FactCheckResponse(
        claims=claims,
        summary=summary
    )