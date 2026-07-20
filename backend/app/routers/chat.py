"""POST /api/chat — hybrid retrieval, rerank, and a streamed cited answer (SSE)."""
from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ..deps import get_current_user
from ..generation import stream_answer
from ..models import ChatRequest, CurrentUser
from ..retrieval.hybrid import hybrid_search
from ..retrieval.rerank import rerank
from ..services import supa

log = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


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
async def chat(
    req: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    if not await supa.is_member(user.id, req.workspace_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this workspace")

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

            candidates = await hybrid_search(req.message, req.workspace_id)
            sources = await rerank(req.message, candidates)

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
            async for piece in stream_answer(req.message, sources):
                answer += piece
                yield _sse("token", {"text": piece})

            latency = int((time.perf_counter() - started) * 1000)
            await supa.insert(
                "messages",
                {"conversation_id": conv_id, "role": "assistant", "content": answer,
                 "citations": citations, "route": "simple", "latency_ms": latency,
                 "tokens_in": None, "tokens_out": None, "cost_usd": None, "cache_hit": False},
            )
            yield _sse("done", {"latency_ms": latency, "route": "simple"})

        except Exception as exc:  # noqa: BLE001 — the stream must always terminate cleanly
            log.exception("chat failed")
            yield _sse("error", {"detail": str(exc)[:200]})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
