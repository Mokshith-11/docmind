"""Semantic cache — reuse a prior answer when a near-identical question is asked.

A cache hit (cosine >= 0.95 within the same workspace) skips retrieval, rerank and
generation entirely, which is where nearly all the latency and API cost live.
"""
from __future__ import annotations

import logging

from ..ingestion.embedder import embed_query
from ..ingestion.indexer import _vec
from ..services import supa

log = logging.getLogger(__name__)

THRESHOLD = 0.95


async def lookup(
    query: str, workspace_id: str
) -> tuple[str | None, list, list[float] | None]:
    """Return (answer, citations, query_embedding).

    - hit  -> (answer, citations, embedding)
    - miss -> (None, [], embedding)   — embedding reusable for retrieval/storage
    - embed failure -> (None, [], None)
    """
    try:
        embedding = await embed_query(query)
    except Exception:
        log.exception("cache embed failed")
        return None, [], None

    try:
        hits = await supa.rpc(
            "match_cache", {"query_embedding": _vec(embedding), "ws": workspace_id,
                            "threshold": THRESHOLD, "match_count": 1}
        )
    except Exception:
        log.exception("cache lookup failed")
        return None, [], embedding

    if hits:
        h = hits[0]
        return h["answer"], h.get("citations") or [], embedding
    return None, [], embedding


async def store(query: str, embedding: list[float], answer: str, citations: list,
                workspace_id: str) -> None:
    if not answer.strip():
        return
    try:
        await supa.insert(
            "semantic_cache",
            {"workspace_id": workspace_id, "query": query, "query_embedding": _vec(embedding),
             "answer": answer, "citations": citations},
        )
    except Exception:
        log.exception("cache store failed")
