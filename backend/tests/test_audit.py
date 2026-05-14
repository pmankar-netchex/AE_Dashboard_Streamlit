from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.audit_service import get_audit_service, reset_audit_service


@pytest.fixture(autouse=True)
def _fresh_audit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    from app.config import get_settings
    from app.services.user_service import get_user_service

    get_settings.cache_clear()
    get_user_service.cache_clear()
    reset_audit_service()


def test_write_appends_event() -> None:
    svc = get_audit_service()
    svc.write(actor="me@x", entity="user", action="create", target="bob@x")
    events, _cursor = svc.list()
    assert len(events) == 1
    assert events[0].entity == "user"
    assert events[0].action == "create"
    assert events[0].target == "bob@x"


def test_list_filters_by_entity() -> None:
    svc = get_audit_service()
    svc.write(actor="a@x", entity="user", action="create", target="x")
    svc.write(actor="a@x", entity="soql", action="update", target="S1-COL-C")
    events, _ = svc.list(entity="soql")
    assert len(events) == 1
    assert events[0].entity == "soql"


def test_audit_endpoint_returns_events(client: TestClient) -> None:
    get_audit_service().write(actor="me", entity="user", action="create", target="bob")
    r = client.get("/api/audit")
    assert r.status_code == 200
    body = r.json()
    assert "events" in body
    assert len(body["events"]) == 1


def test_user_endpoints_write_audit(client: TestClient) -> None:
    client.post("/api/users", json={"email": "x@y", "role": "user"})
    client.put("/api/users/x@y", json={"role": "admin"})
    client.delete("/api/users/x@y")
    events, _ = get_audit_service().list()
    actions = [e.action for e in events]
    assert set(actions) == {"create", "update", "delete"}
