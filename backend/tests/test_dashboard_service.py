from __future__ import annotations

from datetime import date

import pandas as pd

from app.services.dashboard_service import build_dashboard_response


def _row(name: str, manager: str, **values) -> dict:
    base = {
        "AE Id": f"id-{name}",
        "AE Name": name,
        "AE Email": f"{name.lower()}@x.com",
        "AE Manager": manager,
    }
    base.update(values)
    return base


def test_build_dashboard_response_shape() -> None:
    df = pd.DataFrame([
        _row("Alice", "Jane", **{"S1-COL-C": 1000, "S1-COL-D": 600, "S1-COL-M": 500}),
        _row("Bob", "Jane", **{"S1-COL-C": 800, "S1-COL-D": 200, "S1-COL-M": 100}),
    ])
    resp = build_dashboard_response(df, period_start=date(2026, 5, 1), period_end=date(2026, 5, 31))
    assert len(resp.rows) == 2
    assert resp.rows[0].ae_name == "Alice"
    assert resp.rows[0].values["S1-COL-D"] == 600
    # KPIs aggregate: sum of S1-COL-C across rows
    quota_ytd = next(k for k in resp.kpi_row_1 if k.col_id == "S1-COL-C")
    assert quota_ytd.value == 1800
    bookings_ytd = next(k for k in resp.kpi_row_1 if k.col_id == "S1-COL-D")
    assert bookings_ytd.value == 800


def test_kpi_percent_uses_average() -> None:
    df = pd.DataFrame([
        _row("A", "M", **{"S1-COL-E": 0.6}),
        _row("B", "M", **{"S1-COL-E": 0.8}),
    ])
    resp = build_dashboard_response(df, period_start=date(2026, 5, 1), period_end=date(2026, 5, 31))
    attain = next(k for k in resp.kpi_row_1 if k.col_id == "S1-COL-E")
    assert attain.is_average is True
    assert abs((attain.value or 0) - 0.7) < 1e-9


def test_all_source_summary_per_row() -> None:
    df = pd.DataFrame([
        _row("A", "M", **{
            "S6-COL-AF": 100, "S6-COL-AM": 50,
            "S6-COL-AH": 200, "S6-COL-AN": 75,
            "S6-COL-AJ": 0, "S6-COL-AO": 0,
            "S6-COL-AL": 50, "S6-COL-AP": 25,
            "S1-COL-M": 150,
        }),
    ])
    resp = build_dashboard_response(df, period_start=date(2026, 5, 1), period_end=date(2026, 5, 31))
    row = resp.all_source_summary[0]
    assert row.total_pipeline == 350  # 100+200+0+50
    assert row.total_bookings == 150
    by_label = {s.label: s for s in row.sources}
    assert by_label["Self Gen"].pipeline == 100
    assert by_label["Self Gen"].bookings == 50
    assert by_label["SDR"].pipeline == 200
    assert by_label["Channel"].pipeline == 0


def test_handles_empty_dataframe() -> None:
    resp = build_dashboard_response(pd.DataFrame(), period_start=date(2026, 5, 1), period_end=date(2026, 5, 31))
    assert resp.rows == []
    assert resp.all_source_summary == []
    # KPI rows still present, all values None
    for k in resp.kpi_row_1 + resp.kpi_row_2:
        assert k.value is None


def test_handles_missing_columns_gracefully() -> None:
    df = pd.DataFrame([_row("A", "M")])  # no numeric cols at all
    resp = build_dashboard_response(df, period_start=date(2026, 5, 1), period_end=date(2026, 5, 31))
    assert resp.rows[0].values["S1-COL-C"] is None
    assert resp.all_source_summary[0].total_pipeline is None
    assert resp.all_source_summary[0].total_bookings is None
