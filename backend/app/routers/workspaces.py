"""Minimal workspace access for Phase 2.

Full CRUD + member management lands in Phase 5; this only guarantees every user
has a workspace to upload documents into.
"""
from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..models import CurrentUser, WorkspaceOut
from ..services import supa

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(user: CurrentUser = Depends(get_current_user)) -> list[WorkspaceOut]:
    """The user's workspaces, creating a default one on first visit."""
    memberships = await supa.select(
        "workspace_members", {"select": "workspace_id", "user_id": f"eq.{user.id}"}
    )
    ids = [m["workspace_id"] for m in memberships]

    if not ids:
        # The add_owner_as_member trigger enrolls the owner for us.
        created = await supa.insert(
            "workspaces", {"name": "My Workspace", "owner_id": user.id}
        )
        return [WorkspaceOut(**created[0])]

    rows = await supa.select(
        "workspaces",
        {"select": "*", "id": f"in.({','.join(ids)})", "order": "created_at.asc"},
    )
    return [WorkspaceOut(**r) for r in rows]
