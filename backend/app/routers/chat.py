"""POST /api/chat — hybrid retrieval, rerank, and a streamed cited answer (SSE)."""
from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ..ratelimit import limiter

from ..agents.multihop import multihop_retrieve
from ..agents.router import classify
from ..agents.table_qa import table_retrieve
from ..deps import get_current_user
from ..generation import stream_answer
from ..limits import enforce_message_limit
from ..models import ChatRequest, CurrentUser
from ..retrieval import cache
from ..retrieval.hybrid import Candidate, hybrid_search
from ..retrieval.rerank import rerank
from ..services import supa

log = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _retrieve(route: str, question: str, workspace_id: str) -> list[Candidate]:
    """Dispatch to the strategy the router chose."""
    if route == "multihop":
        return await multihop_retrieve(question, workspace_id)
    if route == "table":
        return await table_retrieve(question, workspace_id)
    # simple
    return await rerank(question, await hybrid_search(question, workspace_id))


async def _conversation_id(req: ChatRequest, user: CurrentUser) -> str:
    if req.conversation_id:
        return req.conversation_id
    title = req.message[:60] + ("…" if len(req.message) > 60 else "")
    rows = await supa.insert(
        "conversations",
        {"workspace_id": req.workspace_id, "user_id": user.id, "title": title},
    )
    return rows[0]["id"]


@router.post("/chat")
@limiter.limit("20/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    if not await supa.is_member(user.id, req.workspace_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this workspace")
    await enforce_message_limit(req.workspace_id)

    async def events() -> AsyncGenerator[str, None]:
        started = time.perf_counter()
        try:
            conv_id = await _conversation_id(req, user)
            yield _sse("meta", {"conversation_id": conv_id})

            await supa.insert(
                "messages",
                {"conversation_id": conv_id, "role": "user", "content": req.message,
                 "citations": None, "route": None, "latency_ms": None, "tokens_in": None,
                 "tokens_out": None, "cost_usd": None, "cache_hit": False},
            )

            # Semantic cache: a near-identical prior question skips all the work.
            cached_answer, cached_citations, embedding = await cache.lookup(
                req.message, req.workspace_id
            )
            if cached_answer is not None:
                yield _sse("route", {"route": "cache"})
                yield _sse("sources", {"citations": cached_citations})
                yield _sse("token", {"text": cached_answer})
                latency = int((time.perf_counter() - started) * 1000)
                await supa.insert(
                    "messages",
                    {"conversation_id": conv_id, "role": "assistant", "content": cached_answer,
                     "citations": cached_citations, "route": "cache", "latency_ms": latency,
                     "tokens_in": None, "tokens_out": None, "cost_usd": None, "cache_hit": True},
                )
                yield _sse("done", {"latency_ms": latency, "route": "cache", "cache_hit": True})
                return

            route = await classify(req.message)
            yield _sse("route", {"route": route})
            sources = await _retrieve(route, req.message, req.workspace_id)

            # Look up filenames so citations are human-readable.
            names: dict[str, str] = {}
            if sources:
                ids = ",".join({s.document_id for s in sources})
                docs = await supa.select("documents", {"select": "id,filename", "id": f"in.({ids})"})
                names = {d["id"]: d["filename"] for d in docs}

            citations = [
                {"n": i, "document_id": s.document_id,
                 "filename": names.get(s.document_id, "document"),
                 "page": s.page, "chunk_type": s.chunk_type,
                 "excerpt": s.content[:280]}
                for i, s in enumerate(sources, start=1)
            ]
            yield _sse("sources", {"citations": citations})

            answer = ""
            usage: dict = {}
            async for piece in stream_answer(req.message, sources, usage):
                answer += piece
                yield _sse("token", {"text": piece})

            latency = int((time.perf_counter() - started) * 1000)
            await supa.insert(
                "messages",
                {"conversation_id": conv_id, "role": "assistant", "content": answer,
                 "citations": citations, "route": route, "latency_ms": latency,
                 "tokens_in": usage.get("tokens_in"), "tokens_out": usage.get("tokens_out"),
                 "cost_usd": usage.get("cost_usd"), "cache_hit": False},
            )
            if embedding is not None and answer.strip():
                await cache.store(req.message, embedding, answer, citations, req.workspace_id)
            yield _sse("done", {"latency_ms": latency, "route": route, "cache_hit": False})

        except Exception as exc:  # noqa: BLE001 — the stream must always terminate cleanly
            log.exception("chat failed")
            yield _sse("error", {"detail": str(exc)[:200]})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
