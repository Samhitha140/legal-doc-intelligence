"""
services/retrieval.py
Vector search via ChromaDB + Gemini answer generation.
"""

from typing import List, Optional, Dict, Any
import os

from dotenv import load_dotenv

load_dotenv()

TOP_K = int(os.getenv("TOP_K_RESULTS", 5))

LEGAL_SYSTEM_PROMPT = """You are a senior legal document analyst.
Answer ONLY using the retrieved context below.

Rules:
1. Quote the EXACT clause text (verbatim) that supports your answer.
2. State the source document name and page number for every citation.
3. If the answer is not in the context, say "Not found in the provided documents."
4. Highlight any risk flags (uncapped liability, missing limitations, one-sided terms).
5. Be precise and concise — no speculation beyond the provided text.

CONTEXT:
{context}
"""


async def retrieve_and_answer(
    question: str,
    doc_id: Optional[str] = None,
    clause_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    RAG pipeline: embed query → ChromaDB search → Gemini answer + citations.
    """
    from services.embeddings import get_embedding_model
    from vector_store.chroma_client import get_chroma_client

    embedder = get_embedding_model()
    query_embedding = embedder.get_text_embedding(question)

    client = get_chroma_client()
    collection = client.get_collection("legal_clauses")

    total = collection.count()
    n_results = min(TOP_K * 4, total) if total > 0 else TOP_K

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    all_docs = results["documents"][0]
    all_metas = results["metadatas"][0]
    all_distances = results["distances"][0]

    # Debug: show what doc_ids are stored vs what we're filtering for
    stored_ids = list({m.get("doc_id", "MISSING") for m in all_metas})
    print(f"[DEBUG] Queried doc_id={doc_id}")
    print(f"[DEBUG] Stored doc_ids in results: {stored_ids}")
    print(f"[DEBUG] Total chunks returned before filter: {len(all_docs)}")

    # Filter in Python — more reliable than ChromaDB where clause
    filtered = [
        (text, meta, dist)
        for text, meta, dist in zip(all_docs, all_metas, all_distances)
        if (not doc_id or meta.get("doc_id") == doc_id)
        and (not clause_type or meta.get("clause_type") == clause_type)
    ]
    filtered = filtered[:TOP_K]
    print(f"[DEBUG] Chunks after filter: {len(filtered)}")

    docs = [x[0] for x in filtered]
    metas = [x[1] for x in filtered]
    distances = [x[2] for x in filtered]

    if not docs:
        return {
            "answer": "Not found in the provided documents.",
            "citations": [],
            "risk_flag": False,
            "confidence": 0.0,
        }

    context_parts = []
    citations = []
    for i, (text, meta, dist) in enumerate(zip(docs, metas, distances)):
        context_parts.append(
            f"[{i+1}] Document: {meta.get('doc_name', 'unknown')}, "
            f"Page: {meta.get('page', '?')}, "
            f"Clause: {meta.get('clause_name', 'unknown')}\n{text}\n"
        )
        citations.append({
            "doc": meta.get("doc_name", "unknown"),
            "page": meta.get("page", 0),
            "clause": meta.get("clause_name", ""),
            "clause_type": meta.get("clause_type", "general"),
            "text": text[:500],
            "score": round(1 - dist, 4),
        })

    context = "\n\n".join(context_parts)
    prompt = LEGAL_SYSTEM_PROMPT.format(context=context)
    answer, confidence = await _call_llm(prompt, question)

    risk_keywords = ["unlimited", "uncapped", "consequential damages", "indemnify", "sole discretion"]
    risk_flag = any(kw in " ".join(docs).lower() for kw in risk_keywords)

    return {
        "answer": answer,
        "citations": citations,
        "risk_flag": risk_flag,
        "confidence": confidence,
    }


async def _call_llm(system_prompt: str, question: str) -> tuple[str, float]:
    """Call Google Gemini for the grounded legal answer."""
    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{system_prompt}\n\nQuestion: {question}",
            config=types.GenerateContentConfig(
                max_output_tokens=1500,
            ),
        )
        return response.text, 0.90
    except Exception as e:
        print(f"[LLM ERROR] Gemini call failed: {e}")
        return (
            f"⚠️ LLM unavailable ({type(e).__name__}). "
            "Retrieved context was found but could not generate an answer. "
            "Check your GOOGLE_API_KEY in the .env file.",
            0.0,
        )
