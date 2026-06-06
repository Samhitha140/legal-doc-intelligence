"""
routes/upload.py
POST /upload — accepts PDF, runs full ingestion pipeline.
"""

import os
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from services.ingestion import ingest_document

router = APIRouter()

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 50))


class UploadResponse(BaseModel):
    doc_id: str
    doc_name: str
    total_pages: int
    total_chunks: int
    clause_types: dict
    status: str


@router.post("", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF contract for ingestion into the RAG pipeline.
    
    Steps:
    1. Validate file type + size
    2. Save to disk
    3. Run: extract text → clause chunk → embed → store
    4. Return metadata
    """
    # Validate PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    # Check file size (read into memory briefly for size check)
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise HTTPException(413, f"File too large ({size_mb:.1f}MB). Max {MAX_SIZE_MB}MB.")

    # Save file
    doc_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{doc_id}.pdf"

    with open(save_path, "wb") as f:
        f.write(content)

    # Run ingestion pipeline
    try:
        result = await ingest_document(
            pdf_path=str(save_path),
            doc_id=doc_id,
            doc_name=file.filename,
        )
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Ingestion failed: {str(e)}")

    return UploadResponse(**result)
