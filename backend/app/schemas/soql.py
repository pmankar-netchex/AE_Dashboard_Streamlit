from __future__ import annotations

from pydantic import BaseModel


class SoqlEntryOut(BaseModel):
    col_id: str
    display_name: str
    section: str
    description: str
    aggregation: str
    template_default: str
    template_active: str  # override if present, else default
    has_override: bool
    time_filter: bool
    computed: bool
    blocked: bool


class SoqlUpdateIn(BaseModel):
    template: str


class SoqlTestRequest(BaseModel):
    template: str
    ae_user_id: str | None = None
    period: str | None = "this_month"


class SoqlTestResult(BaseModel):
    ok: bool
    value: float | None = None
    total_size: int = 0
    soql: str = ""
    error: str | None = None


class SoqlHistoryRow(BaseModel):
    version: str
    template: str
    saved_by: str
    saved_at: str
