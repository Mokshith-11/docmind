"""Shared pydantic schemas."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DocStatus = Literal["processing", "ready", "failed"]


class CurrentUser(BaseModel):
    id: str
    email: str | None = None
    role: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str = "docmind-api"


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class ChatRequest(BaseModel):
    workspace_id: str
    message: str
    conversation_id: str | None = None


class Citation(BaseModel):
    n: int
    document_id: str
    filename: str
    page: int | None = None
    chunk_type: str = "text"
    excerpt: str = ""


class WorkspaceOut(BaseModel):
    id: str
    name: str
    owner_id: str
    plan: str = "free"
    created_at: datetime | None = None


class UploadAccepted(BaseModel):
    id: str
    status: DocStatus


class DocumentOut(BaseModel):
    id: str
    workspace_id: str
    filename: str
    storage_path: str
    status: DocStatus
    page_count: int | None = None
    has_tables: bool = False
    has_images: bool = False
    created_at: datetime | None = None
