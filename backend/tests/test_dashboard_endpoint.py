from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def fake_dashboard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace fetch_dashboard with a synthetic two-AE result."""
    from app.services import dashboard_service

    def fake(_sf, _params, start, end):
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
                },
                {
                    "AE Id": "id-2",
                    "AE Name": "Bob",
                    "AE Email": "bob@x",
                    "AE Manager": "Jane",
                    "S1-COL-C": 800,
                    "S1-COL-D": 200,
                    "S1-COL-M": 100,
                },
            ]
        )
        return dashboard_service.build_dashboard_response(df, period_start=start, period_end=end)

    monkeypatch.setattr(dashboard_service, "fetch_dashboard", fake)
    # The router imported the function by name — patch its module too.
    from app.routers import dashboard as dashboard_router

    monkeypatch.setattr(dashboard_router, "fetch_dashboard", fake)
    # Also replace get_sf_client so we never construct a real one
    from app.routers import dashboard as _dr

    monkeypatch.setattr(_dr, "get_sf_client", lambda: None)


def test_dashboard_endpoint_returns_payload(client: TestClient, fake_dashboard) -> None:
    r = client.get("/api/dashboard?period=this_month")
    assert r.status_code == 200
    body = r.json()
    assert len(body["rows"]) == 2
    assert body["rows"][0]["ae_name"] == "Alice"
    assert body["kpi_row_1"][0]["col_id"] == "S1-COL-C"


def test_dashboard_endpoint_accepts_custom_range(client: TestClient, fake_dashboard) -> None:
    r = client.get(
        "/api/dashboard?period=custom&from=2026-01-01&to=2026-03-31"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["period_start"] == "2026-01-01"
    assert body["period_end"] == "2026-03-31"


def test_dashboard_endpoint_requires_auth_in_prod(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_dashboard
) -> None:
    monkeypatch.setenv("ENV", "prod")
    from app.config import get_settings

    get_settings.cache_clear()
    r = client.get("/api/dashboard?period=this_month")
    assert r.status_code == 401
