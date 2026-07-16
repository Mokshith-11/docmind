"""Auth dependency: verify a Supabase-issued JWT.

Supabase issues user session tokens signed either with the legacy shared secret
(HS256) or with an asymmetric signing key (ES256/RS256) published at the project's
JWKS endpoint. This verifies whichever the incoming token uses.
"""
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import settings
from .models import CurrentUser

_bearer = HTTPBearer(auto_error=True)
_ASYMMETRIC = ("ES256", "RS256", "EdDSA")


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    return PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


def _decode(token: str) -> dict:
    alg = jwt.get_unverified_header(token).get("alg")
    if alg in _ASYMMETRIC:
        key = _jwk_client().get_signing_key_from_jwt(token).key
        return jwt.decode(token, key, algorithms=list(_ASYMMETRIC), audience="authenticated")
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET is not configured",
        )
    return jwt.decode(
        token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated"
    )


def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    try:
        payload = _decode(cred.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub")
    return CurrentUser(id=sub, email=payload.get("email"), role=payload.get("role"))
