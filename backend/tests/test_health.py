from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_me_requires_auth():
    r = client.get("/api/me")
    assert r.status_code in (401, 403)  # no bearer token → rejected


def test_me_accepts_valid_hs256(monkeypatch):
    import time

    import jwt

    from app import deps

    monkeypatch.setattr(deps.settings, "supabase_jwt_secret", "test-secret")
    token = jwt.encode(
        {"sub": "user-1", "aud": "authenticated", "role": "authenticated",
         "email": "t@example.com", "exp": int(time.time()) + 60},
        "test-secret",
        algorithm="HS256",
    )
    r = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["id"] == "user-1"
