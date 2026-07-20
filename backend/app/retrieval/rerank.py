"""Cohere Rerank — cross-encoder reordering of the fused candidates.

Embeddings are a bi-encoder: each chunk is compressed to a vector before it ever
sees the question. A cross-encoder reads query and passage together, so it
resolves nuance a single vector loses. It's far more expensive per pair, which is
why it only runs on the ~20 fused candidates rather than the whole corpus.
"""
from __future__ import annotations

import logging

import httpx

from ..config import settings
from .hybrid import Candidate

log = logging.getLogger(__name__)

MODEL = "rerank-v3.5"
URL = "https://api.cohere.com/v2/rerank"
TOP_N = 5
_TIMEOUT = httpx.Timeout(30.0)


async def rerank(query: str, candidates: list[Candidate], top_n: int = TOP_N) -> list[Candidate]:
    """Return the top_n most relevant candidates. Falls back to RRF order on failure."""
    if not candidates:
        return []
    if not settings.cohere_api_key:
        log.warning("COHERE_API_KEY not set — falling back to RRF order")
        return candidates[:top_n]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(
                URL,
                headers={
                    "Authorization": f"Bearer {settings.cohere_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "query": query,
                    "documents": [c_.content for c_ in candidates],
                    "top_n": min(top_n, len(candidates)),
                },
            )
            if r.status_code != 200:
                log.warning("Cohere rerank %s: %s", r.status_code, r.text[:200])
                return candidates[:top_n]

            out: list[Candidate] = []
            for res in r.json().get("results", []):
                cand = candidates[res["index"]]
                cand.score = res["relevance_score"]
                out.append(cand)
            return out
    except Exception:
        # Reranking is a quality boost, not a correctness requirement — degrade gracefully.
        log.exception("rerank failed; using RRF order")
        return candidates[:top_n]
