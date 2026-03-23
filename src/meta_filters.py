"""
Meta filter utilities: fiscal year, time period, filter param builder.
[spec: Section A]
"""
from __future__ import annotations
from datetime import date, timedelta
import calendar


FISCAL_YEAR_START_MONTH = 1  # January — change if fiscal year differs


def fiscal_year_start(today: date | None = None) -> date:
    """Return first day of current fiscal year."""
    d = today or date.today()
    return date(d.year, FISCAL_YEAR_START_MONTH, 1)


def this_month_range() -> tuple[date, date]:
    today = date.today()
    start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    return start, today.replace(day=last_day)


def next_month_range() -> tuple[date, date]:
    today = date.today()
    if today.month == 12:
        nm = date(today.year + 1, 1, 1)
    else:
        nm = date(today.year, today.month + 1, 1)
    last_day = calendar.monthrange(nm.year, nm.month)[1]
    return nm, nm.replace(day=last_day)


def last_week_range() -> tuple[date, date]:
    today = date.today()
    start = today - timedelta(days=today.weekday() + 7)
    end = start + timedelta(days=6)
    return start, end


def this_week_range() -> tuple[date, date]:
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def last_month_range() -> tuple[date, date]:
    today = date.today()
    first_this_month = today.replace(day=1)
    last_prev = first_this_month - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


def resolve_time_period(
    preset: str | None,
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> tuple[date, date]:
    """
    Convert a preset string or custom range to (start, end) dates.
    preset options: 'Last Week', 'This Week', 'Last Month', 'This Month', 'Custom'
    """
    mapping = {
        "Last Week": last_week_range,
        "This Week": this_week_range,
        "Last Month": last_month_range,
        "This Month": this_month_range,
    }
    if preset in mapping:
        return mapping[preset]()
    if preset == "Custom" and custom_start and custom_end:
        return custom_start, custom_end
    return this_month_range()


def build_filter_params(
    ae_user_id: str | None,
    ae_email: str | None,
    manager_name: str | None,
    time_start: date,
    time_end: date,
) -> dict:
    """
    Build a dict of filter params consumed by soql_registry.
    Keys: ae_user_id, ae_email, manager_name, time_start, time_end,
          fiscal_year_start, this_month_start, this_month_end,
          next_month_start, next_month_end
    """
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
