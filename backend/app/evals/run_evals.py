"""RAGAS-style eval runner: score the RAG pipeline on the golden set.

For each golden question we run the real pipeline (route -> retrieve -> generate)
and use an LLM judge (Gemini) to score two metrics in [0,1]:

- faithfulness       — is every claim in the answer supported by the retrieved sources?
- answer_relevance   — does the answer actually address the question?

The averages are written to the eval_runs table so the dashboard can chart them.

Run:  python -m app.evals.run_evals <workspace_id>
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

from ..agents.router import classify
from ..config import settings
from ..generation import stream_answer
from ..retrieval.hybrid import Candidate
from ..routers.chat import _retrieve
from ..services import supa

_JUDGE_MODEL = "gemini-2.5-flash"
_BASE = "https://generativelanguage.googleapis.com/v1beta"
_ITEM_DELAY_S = 6.0  # pace under the free-tier per-minute limit (2 Gemini calls/item)

_JUDGE_PROMPT = """You are grading a document-QA system. Given the QUESTION, the SOURCES the
system retrieved, and its ANSWER, score two metrics from 0.0 to 1.0:

- "faithfulness": 1.0 if every claim in the ANSWER is supported by the SOURCES; lower if it
  adds unsupported claims. If the answer correctly says it cannot find the information and the
  SOURCES indeed lack it, score 1.0.
- "answer_relevance": 1.0 if the ANSWER directly addresses the QUESTION; lower if off-topic.

Respond with ONLY JSON: {"faithfulness": <float>, "answer_relevance": <float>}"""


async def _judge(client: httpx.AsyncClient, question: str, sources: list[Candidate], answer: str) -> dict:
    src = "\n\n".join(f"[{i}] {c.content[:500]}" for i, c in enumerate(sources, 1)) or "(none)"
    user = f"QUESTION:\n{question}\n\nSOURCES:\n{src}\n\nANSWER:\n{answer}"
    r = await client.post(
        f"{_BASE}/models/{_JUDGE_MODEL}:generateContent",
        headers={"Content-Type": "application/json", "x-goog-api-key": settings.gemini_api_key},
        json={
            "contents": [{"role": "user", "parts": [{"text": _JUDGE_PROMPT + "\n\n" + user}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 200,
                                 "responseMimeType": "application/json",
                                 "thinkingConfig": {"thinkingBudget": 0}},
        },
    )
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return json.loads("".join(p.get("text", "") for p in parts))


async def run(workspace_id: str) -> dict:
    golden = json.loads((Path(__file__).parent / "golden_set.json").read_text(encoding="utf-8"))
    items = golden["items"]
    faith: list[float] = []
    rel: list[float] = []

    async with httpx.AsyncClient(timeout=90) as client:
        for n, it in enumerate(items):
            if n:
                await asyncio.sleep(_ITEM_DELAY_S)  # stay under the RPM limit
            q = it["question"]
            sources = await _retrieve(await classify(q), q, workspace_id)
            answer = ""
            async for piece in stream_answer(q, sources):
                answer += piece
            try:
                scores = await _judge(client, q, sources, answer)
                faith.append(float(scores["faithfulness"]))
                rel.append(float(scores["answer_relevance"]))
                print(f"  f={scores['faithfulness']:.2f} r={scores['answer_relevance']:.2f}  {q[:50]}")
            except Exception as e:  # noqa: BLE001
                print(f"  (judge failed: {e}) {q[:50]}")

    result = {
        "faithfulness": round(sum(faith) / len(faith), 3) if faith else None,
        "answer_relevance": round(sum(rel) / len(rel), 3) if rel else None,
        "notes": f"golden_set: {len(items)} items, {len(faith)} scored",
    }
    await supa.insert("eval_runs", result)
    return result


if __name__ == "__main__":
    ws = sys.argv[1] if len(sys.argv) > 1 else None
    if not ws:
        print("usage: python -m app.evals.run_evals <workspace_id>")
        raise SystemExit(1)
    out = asyncio.run(run(ws))
    print("\n=== EVAL RESULT ===")
    print(json.dumps(out, indent=2))
