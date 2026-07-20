"""Router classification — CLAUDE.md requires router tests.

These stub the Groq call so they're hermetic (no network, no key needed).
"""
import pytest

from app.agents import router as router_mod
from app.agents.multihop import decompose


async def _fake_groq(payload):
    async def _inner(system, user, model=None):
        return payload
    return _inner


@pytest.mark.parametrize(
    "groq_json,expected",
    [
        ({"route": "simple"}, "simple"),
        ({"route": "multihop"}, "multihop"),
        ({"route": "table"}, "table"),
        ({"route": "TABLE"}, "table"),           # case-insensitive
        ({"classification": "table"}, "table"),  # wrong key -> value scan
        ({"route": "nonsense"}, "simple"),       # invalid -> default
        ({}, "simple"),                          # empty (groq failed) -> default
    ],
)
async def test_classify(monkeypatch, groq_json, expected):
    async def fake(system, user, model=router_mod.__dict__.get("ROUTER_MODEL", "")):
        return groq_json
    monkeypatch.setattr(router_mod, "json_complete", fake)
    assert await router_mod.classify("some question") == expected


async def test_decompose_returns_subquestions(monkeypatch):
    import app.agents.multihop as mh

    async def fake(system, user, model=""):
        return {"subquestions": ["What is A?", "What is B?", ""]}
    monkeypatch.setattr(mh, "json_complete", fake)
    assert await decompose("compare A and B") == ["What is A?", "What is B?"]


async def test_decompose_falls_back_to_original(monkeypatch):
    import app.agents.multihop as mh

    async def fake(system, user, model=""):
        return {}
    monkeypatch.setattr(mh, "json_complete", fake)
    assert await decompose("a simple question") == ["a simple question"]


async def test_decompose_caps_at_four(monkeypatch):
    import app.agents.multihop as mh

    async def fake(system, user, model=""):
        return {"subquestions": [f"q{i}" for i in range(9)]}
    monkeypatch.setattr(mh, "json_complete", fake)
    assert len(await decompose("big question")) == 4
