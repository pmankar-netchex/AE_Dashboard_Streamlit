from __future__ import annotations

import base64
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_current_user, require_admin
from app.schemas.common import CurrentUser


def _build_app() -> FastAPI:
    """Build a tiny app with two routes that depend on the auth chain."""
    from fastapi import Depends

    app = FastAPI()

    @app.get("/whoami")
    def whoami(user: CurrentUser = Depends(get_current_user)) -> dict:
        return {"email": user.email, "role": user.role, "source": user.source}

    @app.get("/admin-only")
    def admin(user: CurrentUser = Depends(require_admin)) -> dict:
        return {"email": user.email}

    return app


def _principal_header(email: str, oid: str = "oid-1") -> str:
    payload = {
        "claims": [
            {"typ": "preferred_username", "val": email},
            {"typ": "oid", "val": oid},
        ],
        "identityProvider": "aad",
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


# ----- dev mode -----


def test_dev_returns_role_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_ROLE", "user")
    monkeypatch.setenv("DEV_USER_EMAIL", "alice@example.com")
    from app.config import get_settings

    get_settings.cache_clear()
    client = TestClient(_build_app())
    r = client.get("/whoami")
    assert r.status_code == 200
    body = r.json()
    assert body == {"email": "alice@example.com", "role": "user", "source": "dev"}


def test_dev_admin_route_allows_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_ROLE", "admin")
    from app.config import get_settings

    get_settings.cache_clear()
    client = TestClient(_build_app())
    assert client.get("/admin-only").status_code == 200


def test_dev_admin_route_rejects_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_ROLE", "user")
    from app.config import get_settings

    get_settings.cache_clear()
    client = TestClient(_build_app())
    assert client.get("/admin-only").status_code == 403


# ----- prod mode -----


@pytest.fixture
def prod_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    from app.config import get_settings
    from app.services.user_service import get_user_service

    get_settings.cache_clear()
    get_user_service.cache_clear()
    return get_user_service


def test_prod_rejects_missing_principal_header(prod_env) -> None:
    client = TestClient(_build_app())
    r = client.get("/whoami")
    assert r.status_code == 401


def test_prod_rejects_garbage_principal_header(prod_env) -> None:
    client = TestClient(_build_app())
    r = client.get("/whoami", headers={"X-MS-CLIENT-PRINCIPAL": "!!garbage!!"})
    assert r.status_code == 401


def test_prod_forbids_user_not_in_table(prod_env) -> None:
    client = TestClient(_build_app())
    r = client.get(
        "/whoami",
        headers={"X-MS-CLIENT-PRINCIPAL": _principal_header("unknown@example.com")},
    )
    assert r.status_code == 403


def test_prod_returns_role_from_users_table(prod_env) -> None:
    from app.services.user_service import UserRow, get_user_service

    svc = get_user_service()
    svc.upsert(UserRow(email="bob@example.com", role="admin", is_active=True), actor="test")

    client = TestClient(_build_app())
    r = client.get(
        "/whoami",
        headers={"X-MS-CLIENT-PRINCIPAL": _principal_header("Bob@Example.com")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "bob@example.com"
    assert body["role"] == "admin"
    assert body["source"] == "entra"


def test_prod_forbids_inactive_user(prod_env) -> None:
    from app.services.user_service import UserRow, get_user_service

    svc = get_user_service()
    svc.upsert(
        UserRow(email="frozen@example.com", role="user", is_active=False), actor="test"
    )

    client = TestClient(_build_app())
    r = client.get(
        "/whoami",
        headers={"X-MS-CLIENT-PRINCIPAL": _principal_header("frozen@example.com")},
    )
    assert r.status_code == 403


def test_prod_require_admin_forbids_user_role(prod_env) -> None:
    from app.services.user_service import UserRow, get_user_service

    svc = get_user_service()
    svc.upsert(UserRow(email="reg@example.com", role="user", is_active=True), actor="t")

    client = TestClient(_build_app())
    r = client.get(
        "/admin-only",
        headers={"X-MS-CLIENT-PRINCIPAL": _principal_header("reg@example.com")},
    )
    assert r.status_code == 403
