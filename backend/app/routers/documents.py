"""Document upload / list / status / delete. Ingestion runs in the background."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from ..deps import get_current_user
from ..ingestion.indexer import ingest_document
from ..limits import enforce_document_limit
from ..models import CurrentUser, DocumentOut, UploadAccepted
from ..services import supa

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED = (".pdf", ".docx")
MAX_BYTES = 25 * 1024 * 1024  # 25 MB


async def _require_member(user: CurrentUser, workspace_id: str) -> None:
    if not await supa.is_member(user.id, workspace_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this workspace")


@router.post("", response_model=UploadAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background: BackgroundTasks,
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> UploadAccepted:
    await _require_member(user, workspace_id)
    await enforce_document_limit(workspace_id)

    name = (file.filename or "").strip()
    if not name.lower().endswith(ALLOWED):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF and DOCX files are supported")

    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That file is empty")
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Files must be under 25 MB")

    doc_id = str(uuid.uuid4())
    path = f"{workspace_id}/{doc_id}/{name}"
    await supa.ensure_bucket()
    await supa.upload(path, data, file.content_type or "application/octet-stream")

    rows = await supa.insert(
        "documents",
        {
            "id": doc_id,
            "workspace_id": workspace_id,
            "filename": name,
            "storage_path": path,
            "status": "processing",
        },
    )
    background.add_task(ingest_document, doc_id, workspace_id, path, name)
    return UploadAccepted(id=rows[0]["id"], status="processing")


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    workspace: str,
    user: CurrentUser = Depends(get_current_user),
) -> list[DocumentOut]:
    await _require_member(user, workspace)
    rows = await supa.select(
        "documents",
        {"select": "*", "workspace_id": f"eq.{workspace}", "order": "created_at.desc"},
    )
    return [DocumentOut(**r) for r in rows]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    rows = await supa.select("documents", {"select": "*", "id": f"eq.{document_id}"})
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    doc = rows[0]
    await _require_member(user, doc["workspace_id"])

    await supa.remove(doc["storage_path"])
    await supa.delete("documents", {"id": f"eq.{document_id}"})  # chunks cascade
