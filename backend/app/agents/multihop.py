"""Multi-hop retrieval: decompose → retrieve per sub-question → dedupe → rerank."""
from __future__ import annotations

import asyncio

from ..retrieval.hybrid import Candidate, hybrid_search
from ..retrieval.rerank import rerank
from ..services.groq import json_complete

_SYSTEM = """Break the user's question into 2-4 focused sub-questions that must each be
answered to answer the whole. If it is already simple, return just the original.
Respond with ONLY JSON: {"subquestions": ["...", "..."]}"""


async def decompose(question: str) -> list[str]:
    data = await json_complete(_SYSTEM, question)
    subs = data.get("subquestions")
    if isinstance(subs, list):
        cleaned = [s.strip() for s in subs if isinstance(s, str) and s.strip()]
        if cleaned:
            return cleaned[:4]
    return [question]


async def multihop_retrieve(question: str, workspace_id: str) -> list[Candidate]:
    """Retrieve for each sub-question, union + dedupe, then rerank against the
    ORIGINAL question so the final ranking targets what the user actually asked."""
    subs = await decompose(question)

    results = await asyncio.gather(*(hybrid_search(s, workspace_id) for s in subs))

    by_id: dict[str, Candidate] = {}
    for hits in results:
        for c in hits:
            by_id.setdefault(c.id, c)  # first occurrence keeps its content/page

    return await rerank(question, list(by_id.values()))
