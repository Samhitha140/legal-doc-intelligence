"""
routes/risk.py
GET /risk-score/{doc_id} — per-clause risk flags + aggregate score.
"""

from fastapi import APIRouter, HTTPException
from services.risk_scorer import compute_risk_score

router = APIRouter()


@router.get("/{doc_id}")
async def get_risk_score(doc_id: str):
    """
    Compute and return the risk assessment for a document.
    
    Returns:
    - aggregate_risk_score: 0-100
    - risk_level: CLEAN / LOW / MEDIUM / HIGH / CRITICAL
    - flagged_clauses: list with per-clause flags and descriptions
    - recommendations: actionable bullet points
    """
    try:
        result = await compute_risk_score(doc_id)
    except Exception as e:
        raise HTTPException(500, f"Risk scoring failed: {str(e)}")

    if "error" in result:
        raise HTTPException(404, result["error"])

    return result
