"""Groq chat completions (OpenAI-compatible) — used for routing and decomposition.

Fast Llama inference; we use it for the short structured-output calls that sit on
the request's critical path, where latency matters more than raw quality.
"""
from __future__ import annotations

import json
import logging

import httpx

from ..config import settings

log = logging.getLogger(__name__)

URL = "https://api.groq.com/openai/v1/chat/completions"
ROUTER_MODEL = "llama-3.3-70b-versatile"
_TIMEOUT = httpx.Timeout(20.0)


async def json_complete(system: str, user: str, model: str = ROUTER_MODEL) -> dict:
    """Return a parsed JSON object from a Groq JSON-mode completion.

    Returns {} on any failure — callers must have a sensible default so a Groq
    hiccup degrades gracefully instead of failing the request.
    """
    if not settings.groq_api_key:
        return {}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(
                URL,
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
        if r.status_code != 200:
            log.warning("Groq %s: %s", r.status_code, r.text[:200])
            return {}
        content = r.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception:
        log.exception("Groq json_complete failed")
        return {}
