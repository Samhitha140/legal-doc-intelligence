"""
routes/ask.py
POST /ask — hybrid retrieval + LLM grounded answer + citations.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.retrieval import retrieve_and_answer

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None          # restrict to one doc, or None = all docs
    clause_type: Optional[str] = None     # restrict to clause category


class Citation(BaseModel):
    doc: str
    page: int
    clause: str
    clause_type: str
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]
    risk_flag: bool
    confidence: float


@router.post("", response_model=AskResponse)
async def ask_question(req: AskRequest):
    """
    Answer a legal question using hybrid RAG retrieval.
    
    Example questions:
    - "Which contract has a longer non-compete clause?"
    - "What are Party A's indemnification obligations?"
    - "Is there a limitation of liability clause?"
    """
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty.")

    try:
        result = await retrieve_and_answer(
            question=req.question,
            doc_id=req.doc_id,
            clause_type=req.clause_type,
        )
    except Exception as e:
        raise HTTPException(500, f"Retrieval failed: {str(e)}")

    return AskResponse(**result)
