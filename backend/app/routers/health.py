"""Health + identity routes (Phase 1 skeleton)."""
from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..models import CurrentUser, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/me", response_model=CurrentUser)
def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Protected route — proves end-to-end auth works."""
    return user
