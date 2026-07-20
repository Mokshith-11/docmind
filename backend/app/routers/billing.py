"""Billing via Lemon Squeezy — checkout link + webhook.

Inert until the LEMONSQUEEZY_* env vars are set (see .env.example). The webhook
signature is always verified; unconfigured requests are rejected, not trusted.
"""
from __future__ import annotations

import hashlib
import hmac
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..config import settings
from ..deps import get_current_user
from ..models import CheckoutOut, CurrentUser
from ..services import supa

log = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

_LS_API = "https://api.lemonsqueezy.com/v1"


@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(
    workspace_id: str, user: CurrentUser = Depends(get_current_user)
) -> CheckoutOut:
    if not await supa.is_member(user.id, workspace_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this workspace")
    if not (settings.lemonsqueezy_api_key and settings.lemonsqueezy_variant_id):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Billing is not configured yet")

    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "custom": {"workspace_id": workspace_id},
                    "email": user.email,
                }
            },
            "relationships": {
                "variant": {"data": {"type": "variants", "id": settings.lemonsqueezy_variant_id}},
            },
        }
    }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{_LS_API}/checkouts",
            headers={
                "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
                "Content-Type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json",
            },
            json=payload,
        )
    if r.status_code >= 300:
        log.error("Lemon Squeezy checkout %s: %s", r.status_code, r.text[:300])
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not start checkout")
    url = r.json()["data"]["attributes"]["url"]
    return CheckoutOut(url=url)


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def webhook(request: Request) -> None:
    secret = settings.lemonsqueezy_webhook_secret
    if not secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Billing is not configured")

    body = await request.body()
    signature = request.headers.get("X-Signature", "")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")

    event = await request.json()
    name = event.get("meta", {}).get("event_name", "")
    workspace_id = event.get("meta", {}).get("custom_data", {}).get("workspace_id")
    if not workspace_id:
        return

    if name in ("subscription_created", "subscription_resumed", "subscription_unpaused"):
        await supa.update("workspaces", {"id": f"eq.{workspace_id}"}, {"plan": "pro"})
    elif name in ("subscription_expired", "subscription_cancelled", "subscription_paused"):
        await supa.update("workspaces", {"id": f"eq.{workspace_id}"}, {"plan": "free"})
