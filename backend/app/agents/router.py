"""Query router — classify a question into a retrieval strategy (Groq, JSON mode)."""
from __future__ import annotations

from typing import Literal

from ..services.groq import json_complete

Route = Literal["simple", "multihop", "table"]
_VALID = ("simple", "multihop", "table")

_SYSTEM = """You route questions about a user's documents to the best retrieval strategy.
Respond with ONLY a JSON object of the exact form: {"route": "<value>"}
where <value> is one of:
- "simple"   — a fact or explanation answerable from one place in the text.
- "multihop" — needs facts from several places combined, comparisons, or reasoning
               across sections (e.g. "how does X compare to Y", "why", chains of logic).
- "table"    — the answer lives in tabular data: numbers, rows/columns, prices, totals,
               "how much", "average", "which row", counts.
Output nothing but the JSON object."""


async def classify(question: str) -> Route:
    """Return the route. Defaults to 'simple' on any ambiguity or failure."""
    data = await json_complete(_SYSTEM, question)
    route = str(data.get("route", "")).strip().lower()
    if route in _VALID:
        return route  # type: ignore[return-value]
    # Model sometimes answers under a different key — scan values as a fallback.
    for v in data.values():
        if isinstance(v, str) and v.strip().lower() in _VALID:
            return v.strip().lower()  # type: ignore[return-value]
    return "simple"
