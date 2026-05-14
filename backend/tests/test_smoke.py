from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_me_dev(client: TestClient) -> None:
    r = client.get("/api/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "test@example.com"
    assert body["role"] == "admin"
    assert body["source"] == "dev"
    assert "flags" in body
