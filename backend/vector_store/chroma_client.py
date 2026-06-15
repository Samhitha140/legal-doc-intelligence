import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "legal_clauses"


@dataclass
class TextNode:
    text: str
    id_: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


_node_cache: List[TextNode] = []


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )


def add_nodes(nodes: List[TextNode]) -> None:
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


def get_chroma_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def get_all_nodes() -> List[TextNode]:
    return _node_cache


def get_nodes_by_doc_id(doc_id: str) -> List[TextNode]:
    return [n for n in _node_cache if n.metadata.get("doc_id") == doc_id]


def list_documents() -> List[dict]:
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
    global _node_cache
    node_ids = [n.id_ for n in _node_cache if n.metadata.get("doc_id") == doc_id]

    if node_ids:
        collection = get_chroma_client().get_collection(COLLECTION_NAME)
        collection.delete(ids=node_ids)
        _node_cache = [n for n in _node_cache if n.metadata.get("doc_id") != doc_id]

    return len(node_ids)
