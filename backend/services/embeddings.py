import os
from functools import lru_cache
from typing import List

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


class GeminiEmbedder:
    """gemini-embedding-001 — 768 dimensions, no local model needed."""

    def __init__(self):
        self.model = "gemini-embedding-001"

    def get_text_embedding(self, text: str) -> List[float]:
        result = _client.models.embed_content(
            model=self.model,
            contents=text,
        )
        return list(result.embeddings[0].values)

    def get_text_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.get_text_embedding(t) for t in texts]


@lru_cache(maxsize=1)
def get_embedding_model():
    return GeminiEmbedder()
