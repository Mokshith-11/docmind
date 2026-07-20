"""Observability metrics for the dashboard."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import get_current_user
from ..models import CurrentUser
from ..services import supa

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics(
    workspace: str, user: CurrentUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await supa.is_member(user.id, workspace):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this workspace")
    rows = await supa.rpc("workspace_metrics", {"ws": workspace})
    # The function returns a single jsonb object.
    return rows[0] if isinstance(rows, list) and rows else (rows or {})
