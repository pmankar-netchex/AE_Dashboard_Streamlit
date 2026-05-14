from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _fresh(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    monkeypatch.setenv("SENDGRID_API_KEY", "")  # email skipped in dev
    from app.config import get_settings
    from app.scheduler import reset_scheduler
    from app.services.audit_service import reset_audit_service
    from app.services.email_service import reset_email_service
    from app.services.schedule_service import reset_schedule_service
    from app.services.user_service import get_user_service

    get_settings.cache_clear()
    get_user_service.cache_clear()
    reset_schedule_service()
    reset_audit_service()
    reset_email_service()
    reset_scheduler()


def test_create_schedule_and_list(client: TestClient) -> None:
    r = client.post(
        "/api/schedules",
        json={
            "name": "Weekday 9am",
            "cron": "0 9 * * 1-5",
            "recipients": ["cro@example.com"],
            "subject": "Daily Digest",
            "filters": {},
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Weekday 9am"
    assert body["cron"] == "0 9 * * 1-5"
    assert body["recipients"] == ["cro@example.com"]

    listed = client.get("/api/schedules").json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_invalid_cron_returns_400(client: TestClient) -> None:
    r = client.post(
        "/api/schedules",
        json={
            "name": "bad",
            "cron": "not-a-cron",
            "recipients": ["a@x"],
            "subject": "x",
        },
    )
    assert r.status_code == 400


def test_delete_schedule(client: TestClient) -> None:
    sid = client.post(
        "/api/schedules",
        json={
            "name": "x",
            "cron": "0 9 * * 1",
            "recipients": ["a@x"],
            "subject": "s",
        },
    ).json()["id"]
    assert client.delete(f"/api/schedules/{sid}").status_code == 204
    assert client.get("/api/schedules").json() == []


def test_send_now_runs_render_and_email(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Stub the dashboard fetch so we don't need Salesforce
    from app.services import dashboard_service

    def fake_fetch(_sf, _params, start, end):
        df = pd.DataFrame(
            [
                {
                    "AE Id": "id-1",
                    "AE Name": "Alice",
                    "AE Email": "alice@x",
                    "AE Manager": "Jane",
                    "S1-COL-C": 1000,
                    "S1-COL-D": 600,
                    "S1-COL-M": 500,
                }
            ]
        )
        return dashboard_service.build_dashboard_response(
            df, period_start=start, period_end=end
        )

    monkeypatch.setattr(dashboard_service, "fetch_dashboard", fake_fetch)
    from app.scheduler import jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "get_sf_client", lambda: None, raising=False)

    sid = client.post(
        "/api/schedules",
        json={
            "name": "send-now",
            "cron": "0 9 * * 1",
            "recipients": ["a@x"],
            "subject": "Test",
        },
    ).json()["id"]

    r = client.post(f"/api/schedules/{sid}/send-now")
    assert r.status_code == 200
    body = r.json()
    # SENDGRID_API_KEY unset → ok=True, message_id="" (delivery skipped in dev)
    assert body["ok"] is True
