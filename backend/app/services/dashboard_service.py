"""Dashboard orchestration: filter params → data_engine → response objects."""
from __future__ import annotations

import logging
import math
import time
from datetime import date

import pandas as pd

from app.legacy import data_engine, soql_store
from app.legacy.soql_registry import COLUMN_BY_ID
from app.legacy.time_filters import build_filter_params, resolve_time_period
from app.schemas.dashboard import (
    AEDrillDownResponse,
    AERow,
    AllSourceSummaryCell,
    AllSourceSummaryRow,
    DashboardResponse,
    KpiValue,
)
from app.services.column_meta import (
    ALL_SOURCE_SUMMARY,
    KPI_ROW_1,
    KPI_ROW_2,
    TOTAL_BOOKINGS_COL,
    format_hint,
)
from app.services.roster_service import get_roster_service

logger = logging.getLogger(__name__)


def _safe_float(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def resolve_filter_params(
    *,
    manager: str | None,
    ae_user_id: str | None,
    ae_email: str | None,
    period: str | None,
    custom_start: date | None,
    custom_end: date | None,
) -> tuple[dict, date, date]:
    start, end = resolve_time_period(period, custom_start, custom_end)
    params = build_filter_params(
        ae_user_id=ae_user_id,
        ae_email=ae_email,
        manager_name=manager,
        time_start=start,
        time_end=end,
    )
    return params, start, end


def _all_source_summary_row(ae_id: str, ae_name: str, ae_manager: str, row: dict) -> AllSourceSummaryRow:
    pipeline_cols = [p for _, p, _ in ALL_SOURCE_SUMMARY if p]
    total_pipeline_vals = [_safe_float(row.get(c)) for c in pipeline_cols]
    has_any = any(v is not None for v in total_pipeline_vals)
    total_pipeline = (
        sum(v for v in total_pipeline_vals if v is not None) if has_any else None
    )

    total_bookings = _safe_float(row.get(TOTAL_BOOKINGS_COL))

    sources = [
        AllSourceSummaryCell(
            label=label,
            pipeline=_safe_float(row.get(p)),
            bookings=_safe_float(row.get(b)),
        )
        for label, p, b in ALL_SOURCE_SUMMARY
    ]
    return AllSourceSummaryRow(
        ae_id=ae_id,
        ae_name=ae_name,
        ae_manager=ae_manager,
        total_pipeline=total_pipeline,
        total_bookings=total_bookings,
        sources=sources,
    )


def _kpis_from_df(df: pd.DataFrame, spec: list[tuple[str, bool]]) -> list[KpiValue]:
    out: list[KpiValue] = []
    for col_id, is_avg in spec:
        display = COLUMN_BY_ID[col_id].display_name if col_id in COLUMN_BY_ID else col_id
        if col_id not in df.columns:
            out.append(
                KpiValue(
                    col_id=col_id,
                    is_average=is_avg,
                    display_name=display,
                    format=format_hint(col_id),
                    value=None,
                )
            )
            continue
        numeric = pd.to_numeric(df[col_id], errors="coerce")
        val = numeric.mean() if is_avg else numeric.sum()
        out.append(
            KpiValue(
                col_id=col_id,
                is_average=is_avg,
                display_name=display,
                format=format_hint(col_id),
                value=_safe_float(val),
            )
        )
    return out


def build_dashboard_response(
    df: pd.DataFrame, *, period_start: date, period_end: date
) -> DashboardResponse:
    """Pure transformer: dataframe → response. Safe to unit-test with a fake df."""
    rows: list[AERow] = []
    summary_rows: list[AllSourceSummaryRow] = []

    for record in df.to_dict(orient="records"):
        ae_id = str(record.get("AE Id") or record.get("Id") or "")
        ae_name = str(record.get("AE Name") or "")
        ae_email = str(record.get("AE Email") or "")
        ae_manager = str(record.get("AE Manager") or "")

        values: dict[str, float | None] = {}
        for col_id in COLUMN_BY_ID:
            values[col_id] = _safe_float(record.get(col_id))

        rows.append(
            AERow(
                ae_id=ae_id,
                ae_name=ae_name,
                ae_email=ae_email,
                ae_manager=ae_manager,
                values=values,
            )
        )
        summary_rows.append(
            _all_source_summary_row(ae_id, ae_name, ae_manager, record)
        )

    return DashboardResponse(
        rows=rows,
        all_source_summary=summary_rows,
        kpi_row_1=_kpis_from_df(df, KPI_ROW_1),
        kpi_row_2=_kpis_from_df(df, KPI_ROW_2),
        period_start=period_start,
        period_end=period_end,
        fetched_at=time.time(),
    )


def fetch_dashboard(sf, params: dict, period_start: date, period_end: date) -> DashboardResponse:
    overrides = soql_store.load_queries()
    df = data_engine.build_dashboard_dataframe(sf, params, overrides=overrides)
    return build_dashboard_response(df, period_start=period_start, period_end=period_end)


def fetch_ae_drilldown(
    sf, params: dict, period_start: date, period_end: date, ae_id: str
) -> AEDrillDownResponse | None:
    """Per-AE drill-down. Reruns a scoped query for a single AE."""
    scoped = {**params, "ae_user_id": ae_id}
    overrides = soql_store.load_queries()
    df = data_engine.build_dashboard_dataframe(sf, scoped, overrides=overrides)
    if df.empty:
        return None
    full = build_dashboard_response(df, period_start=period_start, period_end=period_end)
    if not full.rows:
        return None
    row = full.rows[0]
    summary = full.all_source_summary[0]
    roster_entry = get_roster_service().get(row.ae_id)
    sdr_name = roster_entry.sdr_name if roster_entry else ""
    sdr_email = roster_entry.sdr_email if roster_entry else ""
    return AEDrillDownResponse(
        ae_id=row.ae_id,
        ae_name=row.ae_name,
        ae_email=row.ae_email,
        ae_manager=row.ae_manager,
        sdr_name=sdr_name,
        sdr_email=sdr_email,
        values=row.values,
        all_source_summary=summary,
        kpi_row_1=full.kpi_row_1,
        kpi_row_2=full.kpi_row_2,
        period_start=full.period_start,
        period_end=full.period_end,
        fetched_at=full.fetched_at,
    )
