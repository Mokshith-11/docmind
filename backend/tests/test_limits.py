import pytest
from fastapi import HTTPException

import app.limits as limits
from app.limits import FREE_MAX_DOCUMENTS, FREE_MAX_MESSAGES_PER_MONTH, Usage


def test_free_plan_has_limits():
    u = Usage(plan="free", doc_count=0, msg_count_month=0)
    assert u.doc_limit == FREE_MAX_DOCUMENTS
    assert u.msg_limit == FREE_MAX_MESSAGES_PER_MONTH


def test_pro_plan_is_unlimited():
    u = Usage(plan="pro", doc_count=999, msg_count_month=9999)
    assert u.doc_limit is None
    assert u.msg_limit is None


async def _stub_usage(monkeypatch, usage: Usage):
    async def fake(_ws):
        return usage
    monkeypatch.setattr(limits, "get_usage", fake)


async def test_document_limit_blocks_free_at_cap(monkeypatch):
    await _stub_usage(monkeypatch, Usage("free", FREE_MAX_DOCUMENTS, 0))
    with pytest.raises(HTTPException) as e:
        await limits.enforce_document_limit("ws")
    assert e.value.status_code == 402


async def test_document_limit_allows_under_cap(monkeypatch):
    await _stub_usage(monkeypatch, Usage("free", FREE_MAX_DOCUMENTS - 1, 0))
    await limits.enforce_document_limit("ws")  # no raise


async def test_pro_never_blocked(monkeypatch):
    await _stub_usage(monkeypatch, Usage("pro", 10_000, 10_000))
    await limits.enforce_document_limit("ws")
    await limits.enforce_message_limit("ws")


async def test_message_limit_blocks_free_at_cap(monkeypatch):
    await _stub_usage(monkeypatch, Usage("free", 0, FREE_MAX_MESSAGES_PER_MONTH))
    with pytest.raises(HTTPException) as e:
        await limits.enforce_message_limit("ws")
    assert e.value.status_code == 402
