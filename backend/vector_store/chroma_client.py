"""
vector_store/chroma_client.py
Local Chroma vector store — free, no API key needed.
Swap for pinecone_client.py to use Pinecone in production.
"""

import os
from functools import lru_cache
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore

from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "legal_clauses"

# In-memory node cache (for BM25 retriever which needs raw nodes, not just embeddings)
_node_cache: List[TextNode] = []


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    """Persistent Chroma client — data saved to disk between restarts."""
    return chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )


@lru_cache(maxsize=1)
def get_vector_store() -> ChromaVectorStore:
    """LlamaIndex-wrapped Chroma vector store."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # cosine similarity for embeddings
    )
    return ChromaVectorStore(chroma_collection=collection)


def add_nodes(nodes: List[TextNode]) -> None:
    """Store nodes directly in ChromaDB with full metadata preserved."""
    global _node_cache

    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        ids=[n.id_ for n in nodes],
        embeddings=[n.embedding for n in nodes],
        documents=[n.text for n in nodes],
        metadatas=[{k: (str(v) if v is not None else "") for k, v in n.metadata.items()} for n in nodes],
    )

    _node_cache.extend(nodes)


def get_all_nodes() -> List[TextNode]:
    """Return all cached nodes (used by BM25 retriever)."""
    return _node_cache


def get_nodes_by_doc_id(doc_id: str) -> List[TextNode]:
    """Filter cached nodes by document ID."""
    return [n for n in _node_cache if n.metadata.get("doc_id") == doc_id]


def get_nodes_by_clause_type(
    clause_type: str, doc_id: Optional[str] = None
) -> List[TextNode]:
    """Filter nodes by clause type, optionally scoped to one doc."""
    nodes = _node_cache
    if doc_id:
        nodes = [n for n in nodes if n.metadata.get("doc_id") == doc_id]
    return [n for n in nodes if n.metadata.get("clause_type") == clause_type]


def list_documents() -> List[dict]:
    """Return unique documents stored in the vector store."""
    seen = {}
    for node in _node_cache:
        meta = node.metadata
        doc_id = meta.get("doc_id")
        if doc_id and doc_id not in seen:
            seen[doc_id] = {
                "doc_id": doc_id,
                "doc_name": meta.get("doc_name", "unknown"),
                "total_chunks": 0,
            }
        if doc_id:
            seen[doc_id]["total_chunks"] += 1
    return list(seen.values())


def delete_document(doc_id: str) -> int:
    """Remove all chunks for a document from both Chroma and cache."""
    global _node_cache
    node_ids = [n.id_ for n in _node_cache if n.metadata.get("doc_id") == doc_id]
    
    if node_ids:
        collection = get_chroma_client().get_collection(COLLECTION_NAME)
        collection.delete(ids=node_ids)
        _node_cache = [n for n in _node_cache if n.metadata.get("doc_id") != doc_id]
    
    return len(node_ids)
