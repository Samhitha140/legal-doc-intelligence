"""
routes/documents.py
GET /documents — list all ingested documents.
DELETE /documents/{doc_id} — remove a document.
"""

from fastapi import APIRouter, HTTPException
from vector_store.chroma_client import list_documents, delete_document

router = APIRouter()


@router.get("")
async def get_documents():
    """List all documents currently stored in the vector store."""
    docs = list_documents()
    return {"total": len(docs), "documents": docs}


@router.delete("/{doc_id}")
async def remove_document(doc_id: str):
    """Remove a document and all its chunks from the vector store."""
    deleted = delete_document(doc_id)
    if deleted == 0:
        raise HTTPException(404, "Document not found.")
    return {"doc_id": doc_id, "deleted_chunks": deleted, "status": "removed"}
