"""Supabase access via REST + Storage, using the service key.

The service key bypasses RLS, so every caller in `routers/` must check workspace
membership itself — see `is_member`.
"""
from typing import Any

import httpx

from ..config import settings

REST = f"{settings.supabase_url}/rest/v1"
STORAGE = f"{settings.supabase_url}/storage/v1"
BUCKET = "documents"
_TIMEOUT = httpx.Timeout(60.0)


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    if extra:
        h.update(extra)
    return h


def _check(r: httpx.Response) -> None:
    """raise_for_status(), but keep the response body — Supabase puts the real
    reason there (e.g. PGRST102 'All object keys must match')."""
    if r.is_error:
        raise httpx.HTTPStatusError(
            f"{r.status_code} {r.request.method} {r.request.url}: {r.text[:500]}",
            request=r.request,
            response=r,
        )


# ── Postgres (PostgREST) ────────────────────────────────────────────────────
async def insert(table: str, rows: list[dict[str, Any]] | dict[str, Any]) -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(
            f"{REST}/{table}",
            headers=_headers({"Content-Type": "application/json", "Prefer": "return=representation"}),
            json=rows,
        )
        _check(r)
        return r.json()


async def select(table: str, params: dict[str, str]) -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(f"{REST}/{table}", headers=_headers(), params=params)
        _check(r)
        return r.json()


async def update(table: str, params: dict[str, str], patch: dict[str, Any]) -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.patch(
            f"{REST}/{table}",
            headers=_headers({"Content-Type": "application/json", "Prefer": "return=representation"}),
            params=params,
            json=patch,
        )
        _check(r)
        return r.json()


async def delete(table: str, params: dict[str, str]) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.delete(f"{REST}/{table}", headers=_headers(), params=params)
        _check(r)


async def is_member(user_id: str, workspace_id: str) -> bool:
    """Service key bypasses RLS, so membership is enforced here."""
    rows = await select(
        "workspace_members",
        {"select": "user_id", "workspace_id": f"eq.{workspace_id}", "user_id": f"eq.{user_id}"},
    )
    return len(rows) > 0


# ── Storage ─────────────────────────────────────────────────────────────────
async def upload(path: str, data: bytes, content_type: str) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(
            f"{STORAGE}/object/{BUCKET}/{path}",
            headers=_headers({"Content-Type": content_type, "x-upsert": "true"}),
            content=data,
        )
        _check(r)


async def download(path: str) -> bytes:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(f"{STORAGE}/object/{BUCKET}/{path}", headers=_headers())
        _check(r)
        return r.content


async def remove(path: str) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.delete(f"{STORAGE}/object/{BUCKET}/{path}", headers=_headers())
        if r.status_code not in (200, 404):
            _check(r)


async def ensure_bucket() -> bool:
    """Create the private `documents` bucket if missing. Returns True if it exists after."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(f"{STORAGE}/bucket/{BUCKET}", headers=_headers())
        if r.status_code == 200:
            return True
        r = await c.post(
            f"{STORAGE}/bucket",
            headers=_headers({"Content-Type": "application/json"}),
            json={"name": BUCKET, "id": BUCKET, "public": False},
        )
        return r.status_code in (200, 201)
