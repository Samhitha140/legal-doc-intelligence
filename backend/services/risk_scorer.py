"""
services/risk_scorer.py
Per-clause risk classification → aggregate risk score (0-100).

Risk model: rule-based keyword scoring + optional ML classifier.
"""

import re
from typing import List, Dict, Any, Tuple


# ─── Risk rule definitions ─────────────────────────────────────────────────────
# Each rule: (regex_pattern, severity_score, risk_label, description)
# severity_score: 0-25 (additive, capped at 100)

RISK_RULES: List[Tuple[re.Pattern, int, str, str]] = [
    # High severity (15-25 points each)
    (
        re.compile(r"unlimited\s+liability|no\s+cap\s+on\s+liability", re.I),
        25, "CRITICAL", "Uncapped liability — Party exposed to unlimited financial risk"
    ),
    (
        re.compile(r"consequential\s+damages(?!\s+excluded|\s+waived)", re.I),
        20, "HIGH", "Consequential damages not excluded — significant financial exposure"
    ),
    (
        re.compile(r"indemnif.{0,30}all\s+claims|indemnif.{0,30}any\s+and\s+all", re.I),
        18, "HIGH", "Broad indemnification clause — covers 'any and all' claims"
    ),
    (
        re.compile(r"sole\s+discretion", re.I),
        15, "HIGH", "Sole discretion — other party has unilateral decision power"
    ),
    (
        re.compile(r"perpetual.{0,20}irrevocable|irrevocable.{0,20}perpetual", re.I),
        15, "HIGH", "Perpetual & irrevocable grant — cannot be reversed"
    ),

    # Medium severity (8-14 points)
    (
        re.compile(r"non.compete.{0,40}\d+\s+year", re.I),
        12, "MEDIUM", "Multi-year non-compete — restricts future employment"
    ),
    (
        re.compile(r"automatic.{0,20}renew|auto.renew", re.I),
        10, "MEDIUM", "Auto-renewal clause — contract extends without explicit consent"
    ),
    (
        re.compile(r"without\s+cause.{0,30}terminat", re.I),
        10, "MEDIUM", "Termination without cause allowed — no protection against arbitrary ending"
    ),
    (
        re.compile(r"governing\s+law.{0,40}(foreign|international|overseas)", re.I),
        8, "MEDIUM", "Foreign governing law — disputes resolved under foreign jurisdiction"
    ),
    (
        re.compile(r"waive.{0,20}(right|claim|remedy)", re.I),
        8, "MEDIUM", "Rights waiver — party gives up legal remedies"
    ),

    # Low severity (2-7 points)
    (
        re.compile(r"subject\s+to\s+change", re.I),
        5, "LOW", "Terms subject to change — instability in agreement"
    ),
    (
        re.compile(r"as\s+is|as-is", re.I),
        4, "LOW", "'As-is' provision — no warranties on deliverable quality"
    ),
    (
        re.compile(r"liquidated\s+damages", re.I),
        3, "LOW", "Liquidated damages clause — pre-agreed penalty amounts"
    ),
]


def score_clause(clause_text: str) -> Dict[str, Any]:
    """
    Score a single clause against all risk rules.
    Returns flags triggered, partial score, and severity level.
    """
    flags = []
    total_score = 0

    for pattern, severity, level, description in RISK_RULES:
        if pattern.search(clause_text):
            flags.append({
                "severity": level,
                "score": severity,
                "description": description,
                "matched_pattern": pattern.pattern,
            })
            total_score += severity

    # Cap at 100
    total_score = min(total_score, 100)

    return {
        "flags": flags,
        "clause_score": total_score,
        "risk_level": _score_to_level(total_score),
    }


def _score_to_level(score: int) -> str:
    if score >= 60:
        return "CRITICAL"
    elif score >= 35:
        return "HIGH"
    elif score >= 15:
        return "MEDIUM"
    elif score > 0:
        return "LOW"
    return "CLEAN"


async def compute_risk_score(doc_id: str) -> Dict[str, Any]:
    """
    Compute aggregate risk for an entire document.
    Scores all clauses → weighted aggregate → returns risk dashboard data.
    """
    from vector_store.chroma_client import get_nodes_by_doc_id

    nodes = get_nodes_by_doc_id(doc_id)

    if not nodes:
        return {"error": "Document not found or not yet ingested"}

    clause_results = []
    all_flags = []
    total_weighted_score = 0
    max_possible = 0

    for node in nodes:
        meta = node.metadata
        result = score_clause(node.text)
        result["clause_name"] = meta.get("clause_name", "Unknown clause")
        result["clause_type"] = meta.get("clause_type", "general")
        result["page"] = meta.get("page", 0)
        result["text_excerpt"] = node.text[:200] + "..." if len(node.text) > 200 else node.text

        clause_results.append(result)
        all_flags.extend(result["flags"])
        total_weighted_score += result["clause_score"]
        max_possible += 100

    # Normalise aggregate score to 0-100
    if max_possible > 0:
        aggregate_score = int((total_weighted_score / max_possible) * 100)
    else:
        aggregate_score = 0

    # Sort clauses by risk (highest first)
    clause_results.sort(key=lambda x: x["clause_score"], reverse=True)

    # Flag counts by severity
    flag_summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for flag in all_flags:
        flag_summary[flag["severity"]] = flag_summary.get(flag["severity"], 0) + 1

    return {
        "doc_id": doc_id,
        "aggregate_risk_score": aggregate_score,  # 0-100
        "risk_level": _score_to_level(aggregate_score),
        "total_clauses": len(nodes),
        "flagged_clauses": len([c for c in clause_results if c["clause_score"] > 0]),
        "flag_summary": flag_summary,
        "clause_breakdown": clause_results[:20],   # top 20 riskiest clauses
        "recommendations": _generate_recommendations(all_flags),
    }


def _generate_recommendations(flags: List[Dict]) -> List[str]:
    """Generate human-readable recommendations from triggered flags."""
    recs = []
    severities = {f["severity"] for f in flags}

    if "CRITICAL" in severities:
        recs.append("⚠️  CRITICAL: Have legal counsel review uncapped liability provisions before signing.")
    if any("indemnif" in f["description"].lower() for f in flags):
        recs.append("📋  Negotiate to limit indemnification scope to direct damages only.")
    if any("consequential" in f["description"].lower() for f in flags):
        recs.append("📋  Request mutual exclusion of consequential damages.")
    if any("non-compete" in f["description"].lower() for f in flags):
        recs.append("📋  Verify non-compete duration and geographic scope are reasonable.")
    if any("auto-renewal" in f["description"].lower() for f in flags):
        recs.append("📋  Set calendar reminder 90 days before auto-renewal date.")
    if any("sole discretion" in f["description"].lower() for f in flags):
        recs.append("📋  Request objective criteria to replace 'sole discretion' language.")

    if not recs:
        recs.append("✅  No critical risk flags detected. Standard review recommended.")

    return recs
