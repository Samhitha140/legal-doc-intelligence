"""
backend/main.py
FastAPI entry point — mounts all route modules.
Run: uvicorn main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# ─── Import routers ────────────────────────────────────────────────────────────
from routes.upload import router as upload_router
from routes.ask import router as ask_router
from routes.clauses import router as clauses_router
from routes.risk import router as risk_router
from routes.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load model in background after server starts so health check passes immediately
    import asyncio
    async def _warmup():
        await asyncio.sleep(2)
        from services.embeddings import get_embedding_model
        print("🔥 Warming up embedding model...")
        get_embedding_model()
        print("✅ Ready.")
    asyncio.create_task(_warmup())
    yield


app = FastAPI(
    title="Legal Document Intelligence API",
    description="RAG pipeline for legal document Q&A, clause extraction, and risk scoring",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow requests from the React frontend (adjust origin in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(upload_router, prefix="/upload", tags=["upload"])
app.include_router(ask_router, prefix="/ask", tags=["ask"])
app.include_router(clauses_router, prefix="/extract-clauses", tags=["clauses"])
app.include_router(risk_router, prefix="/risk-score", tags=["risk"])
app.include_router(documents_router, prefix="/documents", tags=["documents"])


@app.get("/")
async def root():
    return {"message": "Legal Document Intelligence API", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
