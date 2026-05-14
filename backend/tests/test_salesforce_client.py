from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.services.salesforce_client import (
    SalesforceAuthError,
    SalesforceTokenCache,
    reset_sf_client_cache,
    reset_token_cache,
)


TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"


@pytest.fixture(autouse=True)
def _sf_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SF_CLIENT_ID", "id-1")
    monkeypatch.setenv("SF_CLIENT_SECRET", "secret-1")
    monkeypatch.setenv("SF_LOGIN_URL", "https://login.salesforce.com")
    from app.config import get_settings

    get_settings.cache_clear()
    reset_token_cache()
    reset_sf_client_cache()


def _token_payload(access: str = "tok-A") -> dict:
    return {
        "access_token": access,
        "instance_url": "https://example.my.salesforce.com",
        "id": "https://login.salesforce.com/id/...",
        "token_type": "Bearer",
    }


@respx.mock
def test_token_cache_fetches_on_first_call() -> None:
    route = respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload()))
    cache = SalesforceTokenCache()
    tok = cache.get()
    assert tok.access_token == "tok-A"
    assert tok.instance_url == "https://example.my.salesforce.com"
    assert route.call_count == 1


@respx.mock
def test_token_cache_reuses_unexpired_token() -> None:
    route = respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload()))
    cache = SalesforceTokenCache()
    cache.get()
    cache.get()  # should hit cache, not endpoint
    assert route.call_count == 1


@respx.mock
def test_force_refresh_always_fetches() -> None:
    route = respx.post(TOKEN_URL).mock(
        side_effect=[
            Response(200, json=_token_payload("tok-A")),
            Response(200, json=_token_payload("tok-B")),
        ]
    )
    cache = SalesforceTokenCache()
    a = cache.get()
    b = cache.force_refresh()
    assert a.access_token == "tok-A"
    assert b.access_token == "tok-B"
    assert route.call_count == 2


@respx.mock
def test_token_cache_raises_when_credentials_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SF_CLIENT_ID", "")
    monkeypatch.setenv("SF_CLIENT_SECRET", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(SalesforceAuthError, match="not configured"):
        SalesforceTokenCache().get()


@respx.mock
def test_token_cache_records_last_error_on_bad_response() -> None:
    respx.post(TOKEN_URL).mock(return_value=Response(400, text="bad request"))
    cache = SalesforceTokenCache()
    with pytest.raises(SalesforceAuthError):
        cache.get()
    s = cache.status()
    assert s.last_error is not None
    assert "400" in s.last_error


# ---- Router tests ----


@pytest.fixture
def client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())


@respx.mock
def test_status_endpoint_reports_uninitialized(client: TestClient) -> None:
    r = client.get("/api/salesforce/status")
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] is True
    assert body["has_token"] is False


@respx.mock
def test_refresh_endpoint_returns_ok(client: TestClient) -> None:
    respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload()))
    r = client.post("/api/salesforce/refresh")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["instance_url"] == "https://example.my.salesforce.com"


@respx.mock
def test_refresh_endpoint_returns_error_on_failure(client: TestClient) -> None:
    respx.post(TOKEN_URL).mock(return_value=Response(401, text="unauthorized"))
    r = client.post("/api/salesforce/refresh")
    assert r.status_code == 200  # endpoint returns ok=False, not HTTP error
    body = r.json()
    assert body["ok"] is False
    assert body["error"]


def test_refresh_endpoint_requires_admin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEV_ROLE", "user")
    from app.config import get_settings

    get_settings.cache_clear()
    r = client.post("/api/salesforce/refresh")
    assert r.status_code == 403
