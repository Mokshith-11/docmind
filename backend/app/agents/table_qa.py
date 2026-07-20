"""Table Q&A: bias retrieval toward extracted table chunks."""
from __future__ import annotations

from ..retrieval.hybrid import Candidate, hybrid_search
from ..retrieval.rerank import rerank


async def table_retrieve(question: str, workspace_id: str) -> list[Candidate]:
    """Prefer table chunks; fall back to normal retrieval if the doc has none.

    Table chunks carry the markdown-rendered table in `content`, so generation
    reads the actual rows/columns rather than prose that mentions them.
    """
    candidates = await hybrid_search(question, workspace_id)
    tables = [c for c in candidates if c.chunk_type == "table"]

    if not tables:
        return await rerank(question, candidates)

    # Keep tables up top, but retain a few text chunks for surrounding context.
    text = [c for c in candidates if c.chunk_type != "table"]
    return await rerank(question, tables + text[:5])
