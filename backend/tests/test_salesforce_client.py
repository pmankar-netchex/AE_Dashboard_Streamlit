from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.services.salesforce_client import (
    SalesforceAuthError,
    SalesforceSessionError,
    SalesforceTokenCache,
    SfClient,
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


# ---- 401 retry behavior ----


class _FakeSfFactory:
    """Records every Salesforce(...) construction and the .query() outcome.

    Lets a test simulate a stale bearer header (first instance keeps 401-ing
    even after session_id is mutated) and confirm SfClient actually rebuilds.
    """

    def __init__(self, accept_token: str) -> None:
        self.accept_token = accept_token
        self.instances: list[_FakeSf] = []

    def __call__(self, *, instance_url: str, session_id: str):
        inst = _FakeSf(self, instance_url, session_id)
        self.instances.append(inst)
        return inst


class _FakeSf:
    def __init__(self, factory: _FakeSfFactory, instance_url: str, session_id: str):
        self.factory = factory
        self.instance_url = instance_url
        self.session_id = session_id  # initial bearer
        self._initial_session_id = session_id  # simulates cached self.headers
        self.calls = 0

    def query(self, soql: str) -> dict:
        from simple_salesforce.exceptions import SalesforceExpiredSession

        self.calls += 1
        # Real simple_salesforce uses the bearer header captured at __init__,
        # so we deliberately check _initial_session_id, not session_id.
        if self._initial_session_id == self.factory.accept_token:
            return {"records": [{"x": 1}], "totalSize": 1}
        raise SalesforceExpiredSession(
            url="https://example/", status=401, resource_name="query", content=[]
        )


@respx.mock
def test_query_retries_after_401_and_rebuilds_with_new_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Two token responses: stale tok-A, then valid tok-B.
    respx.post(TOKEN_URL).mock(
        side_effect=[
            Response(200, json=_token_payload("tok-A")),
            Response(200, json=_token_payload("tok-B")),
        ]
    )
    factory = _FakeSfFactory(accept_token="tok-B")
    monkeypatch.setattr("simple_salesforce.Salesforce", factory)

    client = SfClient(cache=SalesforceTokenCache())
    result = client.query("SELECT Id FROM User")

    assert result == {"records": [{"x": 1}], "totalSize": 1}
    # Must have constructed a *new* Salesforce instance after refresh — not just
    # mutated session_id on the stale one.
    assert len(factory.instances) == 2
    assert factory.instances[0]._initial_session_id == "tok-A"
    assert factory.instances[1]._initial_session_id == "tok-B"


@respx.mock
def test_query_raises_session_error_when_retry_also_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    respx.post(TOKEN_URL).mock(
        side_effect=[
            Response(200, json=_token_payload("tok-A")),
            Response(200, json=_token_payload("tok-B")),
        ]
    )
    factory = _FakeSfFactory(accept_token="never-matches")
    monkeypatch.setattr("simple_salesforce.Salesforce", factory)

    client = SfClient(cache=SalesforceTokenCache())
    with pytest.raises(SalesforceSessionError):
        client.query("SELECT Id FROM User")


# ---- Exception handler shape ----


@respx.mock
def test_roster_search_returns_typed_503_on_sf_session_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload()))
    factory = _FakeSfFactory(accept_token="never-matches")
    monkeypatch.setattr("simple_salesforce.Salesforce", factory)

    r = client.get("/api/roster/search")
    assert r.status_code == 503
    body = r.json()
    assert body["error_code"] == "sf_session_expired"
    assert body["instance_url"] == "https://example.my.salesforce.com"
    assert "Expired session" in body["error"]
