"""Pure time/filter helpers — fiscal-year math, period resolution, and the
Salesforce filter-param builder consumed by `data_engine`."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

FISCAL_YEAR_START_MONTH = 1  # January — change if fiscal year differs


def fiscal_year_start(today: date | None = None) -> date:
    d = today or date.today()
    return date(d.year, FISCAL_YEAR_START_MONTH, 1)


def this_month_range(today: date | None = None) -> tuple[date, date]:
    d = today or date.today()
    start = d.replace(day=1)
    last_day = calendar.monthrange(d.year, d.month)[1]
    return start, d.replace(day=last_day)


def next_month_range(today: date | None = None) -> tuple[date, date]:
    d = today or date.today()
    if d.month == 12:
        nm = date(d.year + 1, 1, 1)
    else:
        nm = date(d.year, d.month + 1, 1)
    last_day = calendar.monthrange(nm.year, nm.month)[1]
    return nm, nm.replace(day=last_day)


def this_week_range(today: date | None = None) -> tuple[date, date]:
    d = today or date.today()
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def last_week_range(today: date | None = None) -> tuple[date, date]:
    d = today or date.today()
    start = d - timedelta(days=d.weekday() + 7)
    return start, start + timedelta(days=6)


def last_month_range(today: date | None = None) -> tuple[date, date]:
    d = today or date.today()
    first_this_month = d.replace(day=1)
    last_prev = first_this_month - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


# Preset identifiers — also returned by /api/filters/time-presets.
PRESETS: dict[str, callable] = {
    "this_week": this_week_range,
    "last_week": last_week_range,
    "this_month": this_month_range,
    "last_month": last_month_range,
}


def resolve_time_period(
    preset: str | None,
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> tuple[date, date]:
    """Convert a preset id or custom range to (start, end) dates."""
    if preset == "custom" and custom_start and custom_end:
        return custom_start, custom_end
    fn = PRESETS.get(preset or "")
    if fn is not None:
        return fn()
    return this_month_range()


def build_filter_params(
    *,
    ae_user_id: str | None = None,
    ae_email: str | None = None,
    manager_name: str | None = None,
    time_start: date,
    time_end: date,
) -> dict:
    """Build the dict consumed by soql_registry.build_query()."""
    tm_start, tm_end = this_month_range()
    nm_start, nm_end = next_month_range()
    return {
        "ae_user_id": ae_user_id,
        "ae_email": ae_email,
        "manager_name": manager_name,
        "time_start": time_start.strftime("%Y-%m-%dT00:00:00Z"),
        "time_end": time_end.strftime("%Y-%m-%dT23:59:59Z"),
        "time_start_date": time_start.strftime("%Y-%m-%d"),
        "time_end_date": time_end.strftime("%Y-%m-%d"),
        "fiscal_year_start": fiscal_year_start().strftime("%Y-%m-%d"),
        "this_month_start": tm_start.strftime("%Y-%m-%d"),
        "this_month_end": tm_end.strftime("%Y-%m-%d"),
        "next_month_start": nm_start.strftime("%Y-%m-%d"),
        "next_month_end": nm_end.strftime("%Y-%m-%d"),
    }
