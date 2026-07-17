"""Embeddings via Gemini `gemini-embedding-001`, pinned to 768 dims.

768 is not the model default (3072) — it's requested explicitly so vectors match
the `chunks.embedding vector(768)` column and its HNSW index.
"""
from __future__ import annotations

import httpx

from ..config import settings

MODEL = "gemini-embedding-001"
DIMS = 768
_BASE = "https://generativelanguage.googleapis.com/v1beta"
_BATCH = 100
_TIMEOUT = httpx.Timeout(120.0)


class EmbeddingError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    if not settings.gemini_api_key:
        raise EmbeddingError("GEMINI_API_KEY is not configured")
    return {"Content-Type": "application/json", "x-goog-api-key": settings.gemini_api_key}


async def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embed many texts. Returns one 768-dim vector per input, in order."""
    if not texts:
        return []

    vectors: list[list[float]] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        for start in range(0, len(texts), _BATCH):
            batch = texts[start : start + _BATCH]
            payload = {
                "requests": [
                    {
                        "model": f"models/{MODEL}",
                        "content": {"parts": [{"text": t}]},
                        "outputDimensionality": DIMS,
                        "taskType": task_type,
                    }
                    for t in batch
                ]
            }
            r = await c.post(
                f"{_BASE}/models/{MODEL}:batchEmbedContents", headers=_headers(), json=payload
            )
            if r.status_code != 200:
                raise EmbeddingError(f"Gemini embed failed ({r.status_code}): {r.text[:300]}")
            for e in r.json().get("embeddings", []):
                v = e.get("values", [])
                if len(v) != DIMS:
                    raise EmbeddingError(f"Expected {DIMS} dims, got {len(v)}")
                vectors.append(v)

    if len(vectors) != len(texts):
        raise EmbeddingError(f"Embedded {len(vectors)} of {len(texts)} texts")
    return vectors


async def embed_query(text: str) -> list[float]:
    """Single query embedding (Phase 3 retrieval uses the QUERY task type)."""
    v = await embed_texts([text], task_type="RETRIEVAL_QUERY")
    return v[0]
