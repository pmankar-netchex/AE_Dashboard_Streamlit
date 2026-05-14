from __future__ import annotations

from fastapi.testclient import TestClient


def test_columns_endpoint_returns_full_payload(client: TestClient) -> None:
    r = client.get("/api/columns")
    assert r.status_code == 200
    body = r.json()
    assert "columns" in body
    assert "sections" in body
    assert "kpi_row_1" in body and len(body["kpi_row_1"]) == 6
    assert "kpi_row_2" in body and len(body["kpi_row_2"]) == 6
    assert "all_source_summary" in body and len(body["all_source_summary"]) == 4
    assert body["total_bookings_col"] == "S1-COL-M"


def test_columns_preserve_registry_order(client: TestClient) -> None:
    body = client.get("/api/columns").json()
    col_ids = [c["col_id"] for c in body["columns"]]
    assert "S1-COL-C" in col_ids
    # First section should appear before later ones
    sections = [s["key"] for s in body["sections"]]
    assert sections[0] == "Pipeline & Quota"
    assert "Marketing" in sections


def test_columns_format_hints(client: TestClient) -> None:
    body = client.get("/api/columns").json()
    by_id = {c["col_id"]: c for c in body["columns"]}
    assert by_id["S1-COL-C"]["format"] == "currency"
    assert by_id["S1-COL-E"]["format"] == "percent"
    # Lower-is-better flag set for the documented column
    assert by_id["S1-COL-N"]["lower_is_better"] is True
    assert by_id["S1-COL-C"]["lower_is_better"] is False
