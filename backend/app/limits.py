"""Plan limits and usage enforcement."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from .services import supa

# Free tier caps; Pro is unlimited.
FREE_MAX_DOCUMENTS = 3
FREE_MAX_MESSAGES_PER_MONTH = 50


@dataclass
class Usage:
    plan: str
    doc_count: int
    msg_count_month: int

    @property
    def doc_limit(self) -> int | None:
        return None if self.plan == "pro" else FREE_MAX_DOCUMENTS

    @property
    def msg_limit(self) -> int | None:
        return None if self.plan == "pro" else FREE_MAX_MESSAGES_PER_MONTH


async def get_usage(workspace_id: str) -> Usage:
    ws = await supa.select("workspaces", {"select": "plan", "id": f"eq.{workspace_id}"})
    plan = ws[0]["plan"] if ws else "free"
    rows = await supa.rpc("workspace_usage", {"ws": workspace_id})
    row = rows[0] if rows else {"doc_count": 0, "msg_count_month": 0}
    return Usage(plan=plan, doc_count=row["doc_count"], msg_count_month=row["msg_count_month"])


async def enforce_document_limit(workspace_id: str) -> None:
    u = await get_usage(workspace_id)
    if u.doc_limit is not None and u.doc_count >= u.doc_limit:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Free plan is limited to {u.doc_limit} documents. Upgrade to Pro for unlimited.",
        )


async def enforce_message_limit(workspace_id: str) -> None:
    u = await get_usage(workspace_id)
    if u.msg_limit is not None and u.msg_count_month >= u.msg_limit:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Free plan is limited to {u.msg_limit} messages/month. Upgrade to Pro for unlimited.",
        )
