import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv

load_dotenv()


class LocalEmbedder:
    """sentence-transformers all-MiniLM-L6-v2 — free, no API key, 384 dimensions."""

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def get_text_embedding(self, text: str) -> List[float]:
        return self.model.encode(text, convert_to_numpy=True).tolist()

    def get_text_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()


@lru_cache(maxsize=1)
def get_embedding_model():
    return LocalEmbedder()
