from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.dashboard import DashboardResponse
from app.services.column_meta import ALL_SOURCE_SUMMARY

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _money(v) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "—"
    return f"${v:,.0f}"


def _percent(v) -> str:
    if v is None:
        return "—"
    return f"{(v * 100):.1f}%"


def _number(v) -> str:
    if v is None:
        return "—"
    return f"{int(v):,}"


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["money"] = _money
    env.filters["percent"] = _percent
    env.filters["number"] = _number
    return env


def render_all_source_summary(
    response: DashboardResponse,
    *,
    subject: str = "AE Performance — All Source Summary",
) -> str:
    env = _make_env()
    template = env.get_template("all_source_summary.html")
    fetched = datetime.fromtimestamp(response.fetched_at, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    return template.render(
        subject=subject,
        period_start=response.period_start.isoformat(),
        period_end=response.period_end.isoformat(),
        fetched_at=fetched,
        sources=[{"label": s[0]} for s in ALL_SOURCE_SUMMARY],
        ass_rows=[row.model_dump() for row in response.all_source_summary],
        kpis=[k.model_dump() for k in [*response.kpi_row_1, *response.kpi_row_2]],
    )
