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
