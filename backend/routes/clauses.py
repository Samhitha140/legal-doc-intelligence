"""
routes/clauses.py
POST /extract-clauses — metadata-filtered clause retrieval across all docs.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

VALID_CLAUSE_TYPES = [
    "indemnity", "termination", "ip_assignment", "confidentiality",
    "non_compete", "liability", "force_majeure", "governing_law",
    "dispute_resolution", "payment_terms", "warranty", "representations", "general",
]


class ClauseRequest(BaseModel):
    clause_type: str                    # e.g. "indemnity"
    doc_id: Optional[str] = None       # None = search all documents


class ClauseResult(BaseModel):
    doc_name: str
    doc_id: str
    page: int
    clause_name: str
    clause_type: str
    text: str


class ClauseResponse(BaseModel):
    clause_type: str
    total_found: int
    clauses: List[ClauseResult]


@router.post("", response_model=ClauseResponse)
async def extract_clauses(req: ClauseRequest):
    """
    Extract all clauses of a specific type across one or all documents.
    Uses metadata-filtered retrieval (no LLM call needed — pure vector store query).
    
    Example:
      {"clause_type": "indemnity"}
      → Returns all indemnification clauses from all uploaded contracts.
    """
    if req.clause_type not in VALID_CLAUSE_TYPES:
        raise HTTPException(
            400,
            f"Invalid clause_type. Valid options: {', '.join(VALID_CLAUSE_TYPES)}"
        )

    from vector_store.chroma_client import get_nodes_by_clause_type

    nodes = get_nodes_by_clause_type(
        clause_type=req.clause_type,
        doc_id=req.doc_id,
    )

    if not nodes:
        return ClauseResponse(
            clause_type=req.clause_type,
            total_found=0,
            clauses=[],
        )

    clauses = [
        ClauseResult(
            doc_name=n.metadata.get("doc_name", "unknown"),
            doc_id=n.metadata.get("doc_id", ""),
            page=n.metadata.get("page", 0),
            clause_name=n.metadata.get("clause_name", ""),
            clause_type=n.metadata.get("clause_type", "general"),
            text=n.text,
        )
        for n in nodes
    ]

    # Sort by doc_name then page number
    clauses.sort(key=lambda c: (c.doc_name, c.page))

    return ClauseResponse(
        clause_type=req.clause_type,
        total_found=len(clauses),
        clauses=clauses,
    )
