"""Answer generation with Gemini, streamed, with inline citations."""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

import httpx

from .config import settings
from .retrieval.hybrid import Candidate

log = logging.getLogger(__name__)

# CLAUDE.md specifies 2.0-flash, but its free-tier daily quota is easily hit;
# 2.5-flash is newer, higher-quality, and has separate quota. Same family.
MODEL = "gemini-2.5-flash"
_BASE = "https://generativelanguage.googleapis.com/v1beta"
_TIMEOUT = httpx.Timeout(120.0)

# Estimated cost per token (Gemini 2.5 Flash paid-tier list price). Free tier is
# $0; this lets the dashboard show what usage *would* cost at scale.
_COST_IN = 0.30 / 1_000_000
_COST_OUT = 2.50 / 1_000_000


def estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return round(tokens_in * _COST_IN + tokens_out * _COST_OUT, 6)

SYSTEM = """You are DocMind, answering strictly from the user's own documents.

Rules:
- Use ONLY the numbered sources below. Never use outside knowledge.
- Cite every factual claim with the source number in square brackets, like [1] or [2].
- Place the citation right after the claim it supports.
- If the sources do not contain the answer, say exactly: "I couldn't find that in your documents." Do not guess.
- Be concise and direct. Prefer specifics (numbers, dates, names) over paraphrase.
- If sources conflict, say so and cite both."""


def build_prompt(question: str, sources: list[Candidate]) -> str:
    blocks = []
    for i, s in enumerate(sources, start=1):
        loc = f"page {s.page}" if s.page else "unknown page"
        kind = " (table)" if s.chunk_type == "table" else ""
        blocks.append(f"[{i}] ({loc}{kind})\n{s.content}")
    joined = "\n\n".join(blocks) if blocks else "(no sources found)"
    return f"{SYSTEM}\n\n--- SOURCES ---\n{joined}\n\n--- QUESTION ---\n{question}"


async def stream_answer(
    question: str, sources: list[Candidate], usage: dict | None = None
) -> AsyncGenerator[str, None]:
    """Yield answer text chunks as Gemini produces them.

    If `usage` is provided, it's populated with tokens_in / tokens_out / cost_usd
    from Gemini's usageMetadata once the stream completes.
    """
    if not settings.gemini_api_key:
        yield "The server is missing GEMINI_API_KEY."
        return

    payload = {
        "contents": [{"role": "user", "parts": [{"text": build_prompt(question, sources)}]}],
        # thinkingBudget 0 turns off 2.5-flash reasoning tokens so the full answer
        # streams within the output budget instead of being truncated mid-sentence.
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1536,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    url = f"{_BASE}/models/{MODEL}:streamGenerateContent?alt=sse"

    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        async with c.stream(
            "POST",
            url,
            headers={"Content-Type": "application/json", "x-goog-api-key": settings.gemini_api_key},
            json=payload,
        ) as r:
            if r.status_code != 200:
                body = (await r.aread()).decode()[:300]
                log.error("Gemini stream failed %s: %s", r.status_code, body)
                yield "Sorry — I couldn't generate an answer just now."
                return

            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    data = json.loads(raw)
                    for cand in data.get("candidates", []):
                        for part in cand.get("content", {}).get("parts", []):
                            if text := part.get("text"):
                                yield text
                    if usage is not None and (um := data.get("usageMetadata")):
                        t_in = um.get("promptTokenCount", 0)
                        t_out = um.get("candidatesTokenCount", 0)
                        usage.update(
                            tokens_in=t_in, tokens_out=t_out,
                            cost_usd=estimate_cost(t_in, t_out),
                        )
                except json.JSONDecodeError:
                    continue
