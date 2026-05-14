from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _no_azure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    monkeypatch.setenv("DEV_USER_EMAIL", "admin@example.com")
    from app.config import get_settings
    from app.services.user_service import get_user_service

    get_settings.cache_clear()
    get_user_service.cache_clear()


def test_list_users_empty(client: TestClient) -> None:
    assert client.get("/api/users").json() == []


def test_create_user_returns_201(client: TestClient) -> None:
    r = client.post("/api/users", json={"email": "Bob@example.com", "role": "user"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "bob@example.com"
    assert body["role"] == "user"
    assert body["is_active"] is True


def test_create_duplicate_returns_409(client: TestClient) -> None:
    client.post("/api/users", json={"email": "x@example.com", "role": "user"})
    r = client.post("/api/users", json={"email": "x@example.com", "role": "user"})
    assert r.status_code == 409


def test_update_role_persists(client: TestClient) -> None:
    client.post("/api/users", json={"email": "u@x", "role": "user"})
    r = client.put("/api/users/u@x", json={"role": "admin"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_disable_then_list(client: TestClient) -> None:
    client.post("/api/users", json={"email": "u@x", "role": "user"})
    client.put("/api/users/u@x", json={"is_active": False})
    body = client.get("/api/users").json()
    assert body[0]["is_active"] is False


def test_delete_self_forbidden(client: TestClient) -> None:
    client.post("/api/users", json={"email": "admin@example.com", "role": "admin"})
    r = client.delete("/api/users/admin@example.com")
    assert r.status_code == 400


def test_delete_returns_204(client: TestClient) -> None:
    client.post("/api/users", json={"email": "tmp@x", "role": "user"})
    r = client.delete("/api/users/tmp@x")
    assert r.status_code == 204


def test_mutations_require_admin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEV_ROLE", "user")
    from app.config import get_settings

    get_settings.cache_clear()
    assert client.post("/api/users", json={"email": "a@x", "role": "user"}).status_code == 403
    assert client.put("/api/users/a@x", json={"role": "admin"}).status_code == 403
    assert client.delete("/api/users/a@x").status_code == 403
    # GET is allowed for user role
    assert client.get("/api/users").status_code == 200
