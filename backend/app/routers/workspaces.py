"""Workspaces + member management + usage (Phase 5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import get_current_user
from ..limits import get_usage
from ..models import (
    CurrentUser,
    MemberIn,
    MemberOut,
    MemberRole,
    UsageOut,
    WorkspaceIn,
    WorkspaceOut,
)
from ..services import supa

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


async def _role(user_id: str, workspace_id: str) -> str | None:
    rows = await supa.select(
        "workspace_members",
        {"select": "role", "workspace_id": f"eq.{workspace_id}", "user_id": f"eq.{user_id}"},
    )
    return rows[0]["role"] if rows else None


async def _require_role(user_id: str, workspace_id: str, *allowed: str) -> str:
    role = await _role(user_id, workspace_id)
    if role is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this workspace")
    if allowed and role not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(allowed)}")
    return role


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(user: CurrentUser = Depends(get_current_user)) -> list[WorkspaceOut]:
    memberships = await supa.select(
        "workspace_members", {"select": "workspace_id", "user_id": f"eq.{user.id}"}
    )
    ids = [m["workspace_id"] for m in memberships]
    if not ids:
        created = await supa.insert("workspaces", {"name": "My Workspace", "owner_id": user.id})
        return [WorkspaceOut(**created[0])]
    rows = await supa.select(
        "workspaces", {"select": "*", "id": f"in.({','.join(ids)})", "order": "created_at.asc"}
    )
    return [WorkspaceOut(**r) for r in rows]


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceIn, user: CurrentUser = Depends(get_current_user)
) -> WorkspaceOut:
    rows = await supa.insert("workspaces", {"name": body.name.strip() or "Untitled", "owner_id": user.id})
    return WorkspaceOut(**rows[0])


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def rename_workspace(
    workspace_id: str, body: WorkspaceIn, user: CurrentUser = Depends(get_current_user)
) -> WorkspaceOut:
    await _require_role(user.id, workspace_id, "owner", "editor")
    rows = await supa.update("workspaces", {"id": f"eq.{workspace_id}"}, {"name": body.name.strip()})
    return WorkspaceOut(**rows[0])


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str, user: CurrentUser = Depends(get_current_user)
) -> None:
    await _require_role(user.id, workspace_id, "owner")
    await supa.delete("workspaces", {"id": f"eq.{workspace_id}"})  # cascades


@router.get("/{workspace_id}/usage", response_model=UsageOut)
async def workspace_usage(
    workspace_id: str, user: CurrentUser = Depends(get_current_user)
) -> UsageOut:
    await _require_role(user.id, workspace_id)
    u = await get_usage(workspace_id)
    return UsageOut(
        plan=u.plan, doc_count=u.doc_count, doc_limit=u.doc_limit,
        msg_count_month=u.msg_count_month, msg_limit=u.msg_limit,
    )


# ── Members ─────────────────────────────────────────────────────────────────
@router.get("/{workspace_id}/members", response_model=list[MemberOut])
async def list_members(
    workspace_id: str, user: CurrentUser = Depends(get_current_user)
) -> list[MemberOut]:
    await _require_role(user.id, workspace_id)
    rows = await supa.select(
        "workspace_members", {"select": "user_id,role", "workspace_id": f"eq.{workspace_id}"}
    )
    emails = await supa.emails_for([r["user_id"] for r in rows])
    return [MemberOut(user_id=r["user_id"], role=r["role"], email=emails.get(r["user_id"])) for r in rows]


@router.post("/{workspace_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    workspace_id: str, body: MemberIn, user: CurrentUser = Depends(get_current_user)
) -> MemberOut:
    await _require_role(user.id, workspace_id, "owner")
    target = await supa.find_user_by_email(body.email.strip().lower())
    if not target:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No DocMind user with that email. Ask them to sign up first.",
        )
    await supa.insert(
        "workspace_members",
        {"workspace_id": workspace_id, "user_id": target["id"], "role": body.role},
    )
    return MemberOut(user_id=target["id"], role=body.role, email=body.email)


@router.patch("/{workspace_id}/members/{member_id}", response_model=MemberOut)
async def update_member_role(
    workspace_id: str, member_id: str, body: MemberRole,
    user: CurrentUser = Depends(get_current_user),
) -> MemberOut:
    await _require_role(user.id, workspace_id, "owner")
    rows = await supa.update(
        "workspace_members",
        {"workspace_id": f"eq.{workspace_id}", "user_id": f"eq.{member_id}"},
        {"role": body.role},
    )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    emails = await supa.emails_for([member_id])
    return MemberOut(user_id=member_id, role=body.role, email=emails.get(member_id))


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: str, member_id: str, user: CurrentUser = Depends(get_current_user)
) -> None:
    await _require_role(user.id, workspace_id, "owner")
    ws = await supa.select("workspaces", {"select": "owner_id", "id": f"eq.{workspace_id}"})
    if ws and ws[0]["owner_id"] == member_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot remove the workspace owner")
    await supa.delete(
        "workspace_members",
        {"workspace_id": f"eq.{workspace_id}", "user_id": f"eq.{member_id}"},
    )
