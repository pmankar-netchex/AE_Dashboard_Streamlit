from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_list_soql_returns_entries(client: TestClient) -> None:
    r = client.get("/api/soql")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 30
    assert "col_id" in rows[0]
    assert "template_active" in rows[0]


def test_get_unknown_col_id_returns_404(client: TestClient) -> None:
    r = client.get("/api/soql/UNKNOWN-COL")
    assert r.status_code == 404


def test_get_known_col_id_returns_entry(client: TestClient) -> None:
    r = client.get("/api/soql/S1-COL-C")
    assert r.status_code == 200
    body = r.json()
    assert body["col_id"] == "S1-COL-C"
    assert body["template_default"]
    # No override by default
    assert body["has_override"] is False


def test_update_requires_admin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEV_ROLE", "user")
    from app.config import get_settings

    get_settings.cache_clear()
    r = client.put("/api/soql/S1-COL-C", json={"template": "SELECT 1 FROM Account"})
    assert r.status_code == 403


def test_update_with_local_fallback_persists(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    fake = tmp_path / "soql_overrides.json"
    from app.legacy import soql_store
    from app.config import get_settings

    monkeypatch.setattr(soql_store, "_LOCAL_FILE", fake)
    get_settings.cache_clear()

    r = client.put(
        "/api/soql/S1-COL-C",
        json={"template": "SELECT SUM(QuotaAmount) FROM ForecastingQuota"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["has_override"] is True
    assert "SUM(QuotaAmount)" in body["template_active"]


def test_update_blocked_in_prod_without_writes_flag(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "fake-conn-str")
    monkeypatch.delenv("ALLOW_PROD_QUERY_WRITES", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()
    r = client.put("/api/soql/S1-COL-C", json={"template": "SELECT 1 FROM Account"})
    assert r.status_code == 423


def test_history_endpoint_returns_empty_when_unconfigured(client: TestClient) -> None:
    r = client.get("/api/soql/S1-COL-C/history")
    assert r.status_code == 200
    assert r.json() == []
