"""Hybrid retrieval: dense + sparse, fused with Reciprocal Rank Fusion."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from ..ingestion.embedder import embed_query
from ..ingestion.indexer import _vec
from ..services import supa

TOP_K_EACH = 20
RRF_K = 60  # damping constant; 60 is the value from the original RRF paper


@dataclass
class Candidate:
    id: str
    document_id: str
    content: str
    page: int | None
    chunk_type: str
    score: float = 0.0


def reciprocal_rank_fusion(
    lists: list[list[dict]], k: int = RRF_K, limit: int = TOP_K_EACH
) -> list[Candidate]:
    """Fuse ranked lists by rank position, not score.

    Dense similarity (0-1 cosine) and sparse ts_rank are on incomparable scales,
    so averaging them is meaningless. RRF only reads position: a chunk scores
    1/(k+rank) in each list it appears in, summed across lists.
    """
    scores: dict[str, float] = {}
    seen: dict[str, dict] = {}

    for ranked in lists:
        for rank, row in enumerate(ranked, start=1):
            cid = row["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            seen.setdefault(cid, row)

    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    out: list[Candidate] = []
    for cid, score in ordered:
        r = seen[cid]
        out.append(
            Candidate(
                id=cid,
                document_id=r["document_id"],
                content=r["content"],
                page=r.get("page"),
                chunk_type=r.get("chunk_type", "text"),
                score=score,
            )
        )
    return out


async def _dense(query: str, workspace_id: str) -> list[dict]:
    vec = await embed_query(query)
    return await supa.rpc(
        "match_chunks",
        {"query_embedding": _vec(vec), "ws": workspace_id, "match_count": TOP_K_EACH},
    )


def _or_query(query: str) -> str:
    """Turn a natural question into OR-of-terms for the sparse leg.

    websearch_to_tsquery ANDs bare words, so "setup cost" needs BOTH in a chunk
    and misses one that has only "setup". Joining terms with the `or` keyword
    (which websearch_to_tsquery reads as the OR operator) recovers recall;
    reranking then restores precision. English stopwords are dropped by the
    text-search config regardless.
    """
    words = re.findall(r"[A-Za-z0-9]+", query)
    return " or ".join(words)


async def _sparse(query: str, workspace_id: str) -> list[dict]:
    q = _or_query(query)
    if not q:
        return []
    return await supa.rpc(
        "search_chunks",
        {"query_text": q, "ws": workspace_id, "match_count": TOP_K_EACH},
    )


async def hybrid_search(query: str, workspace_id: str) -> list[Candidate]:
    """Run both retrievers concurrently and fuse. Never fails on one leg alone."""
    dense, sparse = await asyncio.gather(
        _dense(query, workspace_id),
        _sparse(query, workspace_id),
        return_exceptions=True,
    )
    lists: list[list[dict]] = []
    for leg in (dense, sparse):
        if isinstance(leg, list):
            lists.append(leg)
    if not lists:
        return []
    return reciprocal_rank_fusion(lists)
