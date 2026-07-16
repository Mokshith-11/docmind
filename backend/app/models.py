"""Shared pydantic schemas."""
from pydantic import BaseModel


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
