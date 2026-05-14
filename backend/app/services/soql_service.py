from __future__ import annotations

import logging
from typing import Any

from app.legacy import data_engine, soql_store
from app.legacy.soql_registry import COLUMN_BY_ID, SOQLEntry, build_query
from app.schemas.soql import (
    SoqlEntryOut,
    SoqlHistoryRow,
    SoqlTestResult,
)

logger = logging.getLogger(__name__)


def list_entries() -> list[SoqlEntryOut]:
    overrides = soql_store.load_queries()
    out: list[SoqlEntryOut] = []
    for entry in COLUMN_BY_ID.values():
        override = overrides.get(entry.col_id)
        out.append(
            SoqlEntryOut(
                col_id=entry.col_id,
                display_name=entry.display_name,
                section=entry.section,
                description=entry.description,
                aggregation=entry.aggregation,
                template_default=entry.template,
                template_active=override or entry.template,
                has_override=bool(override),
                time_filter=entry.time_filter,
                computed=entry.computed,
                blocked=entry.blocked,
            )
        )
    return out


def get_entry(col_id: str) -> SoqlEntryOut | None:
    entry = COLUMN_BY_ID.get(col_id)
    if entry is None:
        return None
    override = soql_store.load_queries().get(col_id)
    return SoqlEntryOut(
        col_id=entry.col_id,
        display_name=entry.display_name,
        section=entry.section,
        description=entry.description,
        aggregation=entry.aggregation,
        template_default=entry.template,
        template_active=override or entry.template,
        has_override=bool(override),
        time_filter=entry.time_filter,
        computed=entry.computed,
        blocked=entry.blocked,
    )


def update_entry(col_id: str, template: str, actor: str) -> None:
    """Persist a new template override. Subject to ALLOW_PROD_QUERY_WRITES gate."""
    if col_id not in COLUMN_BY_ID:
        raise KeyError(col_id)
    soql_store.save_query(col_id, template, actor=actor)
    data_engine.clear_query_failures()


def history(col_id: str, limit: int = 25) -> list[SoqlHistoryRow]:
    return [SoqlHistoryRow(**row) for row in soql_store.load_history(col_id, limit=limit)]


def test_query(
    sf, col_id: str, template: str, params: dict[str, Any]
) -> SoqlTestResult:
    """Run a candidate template against Salesforce as a single-AE query.

    Returns the aggregate value (first field of first record), total size, the
    fully-resolved SOQL string, and any error message.
    """
    entry = COLUMN_BY_ID.get(col_id)
    if entry is None:
        return SoqlTestResult(ok=False, error=f"unknown col_id: {col_id}")

    effective = SOQLEntry(
        col_id=entry.col_id,
        display_name=entry.display_name,
        section=entry.section,
        description=entry.description,
        template=template,
        time_filter=entry.time_filter,
        computed=entry.computed,
        blocked=entry.blocked,
        aggregation=entry.aggregation,
    )
    try:
        soql = build_query(effective, params)
    except Exception as exc:
        return SoqlTestResult(ok=False, error=f"template error: {exc}")

    try:
        result = sf.query(soql.strip())
    except Exception as exc:
        return SoqlTestResult(ok=False, soql=soql, error=str(exc))

    records = result.get("records", [])
    if not records:
        return SoqlTestResult(ok=True, soql=soql, total_size=0, value=None)
    row = records[0]
    val = None
    for k, v in row.items():
        if k != "attributes":
            val = v
            break
    try:
        numeric = float(val) if val is not None else None
    except (TypeError, ValueError):
        numeric = None
    return SoqlTestResult(
        ok=True,
        soql=soql,
        total_size=int(result.get("totalSize", len(records))),
        value=numeric,
    )
