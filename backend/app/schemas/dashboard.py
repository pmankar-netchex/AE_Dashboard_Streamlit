from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class AERow(BaseModel):
    ae_id: str
    ae_name: str
    ae_email: str
    ae_manager: str
    # col_id -> numeric value or None (cells render formatted client-side)
    values: dict[str, float | None]


class KpiValue(BaseModel):
    col_id: str
    is_average: bool
    display_name: str
    format: str
    value: float | None


class AllSourceSummaryRow(BaseModel):
    ae_id: str
    ae_name: str
    ae_manager: str
    total_pipeline: float | None
    total_bookings: float | None
    # one entry per source — label kept here so the front-end is decoupled
    sources: list["AllSourceSummaryCell"]


class AllSourceSummaryCell(BaseModel):
    label: str
    pipeline: float | None
    bookings: float | None


class DashboardResponse(BaseModel):
    rows: list[AERow]
    all_source_summary: list[AllSourceSummaryRow]
    kpi_row_1: list[KpiValue]
    kpi_row_2: list[KpiValue]
    period_start: date
    period_end: date
    fetched_at: float


class AEDrillDownResponse(BaseModel):
    ae_id: str
    ae_name: str
    ae_email: str
    ae_manager: str
    sdr_name: str
    sdr_email: str
    values: dict[str, float | None]
    all_source_summary: AllSourceSummaryRow
    kpi_row_1: list[KpiValue]
    kpi_row_2: list[KpiValue]
    period_start: date
    period_end: date
    fetched_at: float


AllSourceSummaryRow.model_rebuild()
