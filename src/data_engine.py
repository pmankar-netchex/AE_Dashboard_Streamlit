"""
Data Engine — executes SOQL registry queries, builds unified DataFrame.
[spec: Steps 3–5, Critical Rule #3]

Per-SOQL error isolation: if one query fails, only its column shows NaN.
"""
from __future__ import annotations
import logging
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

log = logging.getLogger(__name__)

from src.soql_registry import (
    ALL_COLUMNS, COLUMN_BY_ID, build_query, SOQLEntry, BATCH_FIELD_MAP,
)
from src.meta_filters import build_filter_params


_QUERY_ERROR_KEYWORDS = [
    "malformed_query", "invalid_field", "invalid_type",
    "no such column", "unexpected token", "invalid soql",
]
_non_retryable_failures: dict[str, str] = {}


def clear_query_failures():
    """Reset non-retryable failure cache (call when overrides change)."""
    _non_retryable_failures.clear()


def _is_query_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in _QUERY_ERROR_KEYWORDS)


# ── Single-query helpers (used by SOQL test tab & per-AE fallback) ────────────

def _run_query(sf, soql: str) -> Any:
    """Execute SOQL and return the aggregate value (first field of first record)."""
    result = sf.query(soql.strip())
    records = result.get("records", [])
    if not records:
        return None
    row = records[0]
    for k, v in row.items():
        if k != "attributes":
            return v
    return None


def fetch_column(sf, entry: SOQLEntry, params: dict, overrides: dict | None = None) -> tuple[str, Any]:
    """
    Execute one SOQL entry and return (col_id, value).
    On failure returns (col_id, None) — per-SOQL error isolation.
    """
    if entry.computed or entry.blocked:
        return entry.col_id, None
    if entry.col_id in _non_retryable_failures:
        return entry.col_id, None
    if overrides and entry.col_id in overrides:
        effective_entry = SOQLEntry(
            col_id=entry.col_id,
            display_name=entry.display_name,
            section=entry.section,
            description=entry.description,
            template=overrides[entry.col_id],
            time_filter=entry.time_filter,
            aggregation=entry.aggregation,
        )
    else:
        effective_entry = entry
    soql = build_query(effective_entry, params)
    t0 = time.time()
    try:
        val = _run_query(sf, soql)
        log.debug("%s = %s (%.1fs)", entry.col_id, val, time.time() - t0)
        return entry.col_id, val
    except Exception as exc:
        if _is_query_error(exc):
            _non_retryable_failures[entry.col_id] = str(exc)
            log.error("%s FAILED (non-retryable): %s", entry.col_id, exc)
        else:
            log.warning("%s FAILED: %s", entry.col_id, exc)
        return entry.col_id, None


def fetch_all_columns(sf, params: dict, overrides: dict | None = None) -> dict[str, Any]:
    """
    Run every non-computed, non-blocked SOQL for a single AE.
    Used by SOQL test tab. Dashboard uses batch path instead.
    """
    results: dict[str, Any] = {}
    queryable = [e for e in ALL_COLUMNS if not e.computed and not e.blocked]
    for entry in ALL_COLUMNS:
        if entry.computed or entry.blocked:
            results[entry.col_id] = None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_column, sf, entry, params, overrides): entry
            for entry in queryable
        }
        for future in as_completed(futures):
            col_id, val = future.result()
            results[col_id] = val

    c = results.get("S1-COL-C") or 0
    d = results.get("S1-COL-D") or 0
    f = results.get("S1-COL-F") or 0
    g = results.get("S1-COL-G") or 0
    results["S1-COL-E"] = (d / c) if c else None
    results["S1-COL-H"] = (g / f) if f else None
    return results


# ── Batch query helpers ───────────────────────────────────────────────────────

def _detect_batch_field(template: str) -> tuple[str, str] | None:
    """Return (placeholder, group_by_field) if template is batchable, else None."""
    for placeholder, field in BATCH_FIELD_MAP.items():
        if placeholder in template:
            return placeholder, field
    return None


def _build_batch_soql(entry: SOQLEntry, params: dict, ae_ids: list[str],
                      overrides: dict | None = None) -> tuple[str, str] | None:
    """Transform a single-AE template into a batch GROUP BY query.
    Returns (soql, group_field) or None if not batchable."""
    template = (overrides or {}).get(entry.col_id, entry.template)
    info = _detect_batch_field(template)
    if not info:
        return None
    placeholder, field = info

    id_list = ",".join(f"'{aid}'" for aid in ae_ids)
    batch = template.replace(placeholder, f"{field} IN ({id_list})")
    batch = batch.replace("SELECT ", f"SELECT {field}, ", 1)
    batch = batch.rstrip() + f"\nGROUP BY {field}"

    # Format remaining placeholders (time params); owner clause dummies are unused.
    # Defaults first, then params overrides.
    fmt_kwargs = {
        "owner_clause": "1=1",
        "quota_owner_clause": "1=1",
        "custom_owner_clause": "1=1",
        "activity_owner_clause": "1=1",
        "ae_email_clause": "1=1",
        "sdr_owner_clause": "1=1",
        "sdr_split_owner_clause": "1=1",
        "sdr_user_id": "000000000000000",
        **params,
    }
    batch = batch.format(**fmt_kwargs)
    return batch, field


def _run_batch_query(sf, soql: str, group_field: str) -> dict[str, Any]:
    """Execute batch SOQL, return {group_field_value: aggregate_value}."""
    result = sf.query(soql.strip())
    mapping = {}
    for record in result.get("records", []):
        key = record.get(group_field)
        val = next((v for k, v in record.items() if k not in ("attributes", group_field)), None)
        if key:
            mapping[key] = val
    return mapping


def _fetch_batch(sf, entry: SOQLEntry, soql: str, group_field: str,
                 ae_ids: list[str]) -> tuple[str, dict[str, Any]]:
    """Execute one batch query. Returns (col_id, {ae_id: value})."""
    t0 = time.time()
    try:
        mapping = _run_batch_query(sf, soql, group_field)
        log.debug("%s batch: %d results (%.1fs)", entry.col_id, len(mapping), time.time() - t0)
        return entry.col_id, {aid: mapping.get(aid) for aid in ae_ids}
    except Exception as exc:
        elapsed = time.time() - t0
        if _is_query_error(exc):
            _non_retryable_failures[entry.col_id] = str(exc)
            log.error("%s FAILED (non-retryable, %.1fs): %s", entry.col_id, elapsed, exc)
        else:
            log.warning("%s FAILED (%.1fs): %s", entry.col_id, elapsed, exc)
        return entry.col_id, {aid: None for aid in ae_ids}


# ── AE list & dashboard builder ──────────────────────────────────────────────

_NULL_ID_SENTINEL = "000000000000000"  # well-formed but never-matching SF ID


def resolve_sdr_user_id(sf, ae_user_id: str) -> str:
    """Return the AE's Assigned_SDR_Outbound__c User Id, or a never-matching sentinel."""
    if not ae_user_id:
        return _NULL_ID_SENTINEL
    try:
        r = sf.query(
            f"SELECT Assigned_SDR_Outbound__c FROM User WHERE Id = '{ae_user_id}' LIMIT 1"
        )
        recs = r.get("records", [])
        if recs:
            sdr = recs[0].get("Assigned_SDR_Outbound__c")
            if sdr:
                return sdr
    except Exception:
        pass
    return _NULL_ID_SENTINEL


def build_ae_list(sf, params: dict) -> list[dict]:
    """
    Get the list of AEs to display based on manager/ae_user_id filter.
    Returns list of {Id, Name, Email, Manager, SdrId} dicts.
    """
    if params.get("ae_user_id"):
        query = f"""
            SELECT Id, Name, Email, Manager.Name, Assigned_SDR_Outbound__c
            FROM User
            WHERE Id = '{params["ae_user_id"]}'
            AND IsActive = true
        """
    elif params.get("manager_name"):
        query = f"""
            SELECT Id, Name, Email, Manager.Name, Assigned_SDR_Outbound__c
            FROM User
            WHERE Manager.Name = '{params["manager_name"]}'
            AND IsActive = true
            ORDER BY Name
        """
    else:
        query = """
            SELECT Id, Name, Email, Manager.Name, Assigned_SDR_Outbound__c
            FROM User
            WHERE IsActive = true
            AND User_Role_Formula__c LIKE '%Sales Rep%'
            AND (NOT User_Role_Formula__c LIKE '%SDR%')
            AND (NOT User_Role_Formula__c LIKE '%Account%')
            ORDER BY Name
            LIMIT 200
        """
    try:
        result = sf.query(query)
        return [
            {
                "Id": r["Id"],
                "Name": r["Name"],
                "Email": r.get("Email", ""),
                "Manager": (r.get("Manager") or {}).get("Name", ""),
                "SdrId": r.get("Assigned_SDR_Outbound__c") or _NULL_ID_SENTINEL,
            }
            for r in result.get("records", [])
        ]
    except Exception:
        return []


def build_dashboard_dataframe(sf, params: dict, overrides: dict | None = None) -> pd.DataFrame:
    """
    Build the unified DataFrame with one row per AE and columns C–AD.
    Uses batch queries where possible (GROUP BY), per-AE fallback for SDR queries.
    """
    t_start = time.time()
    ae_list = build_ae_list(sf, params)
    log.info("AE list: %d users (%.1fs)", len(ae_list), time.time() - t_start)
    if not ae_list:
        return pd.DataFrame()

    ae_ids = [ae["Id"] for ae in ae_list]

    # Categorize columns
    batch_jobs = []      # (entry, soql, group_field)
    per_ae_entries = []  # non-batchable (SDR queries)
    skip_ids = set()

    for entry in ALL_COLUMNS:
        if entry.computed or entry.blocked or entry.col_id in _non_retryable_failures:
            skip_ids.add(entry.col_id)
            continue
        batch_info = _build_batch_soql(entry, params, ae_ids, overrides)
        if batch_info:
            batch_jobs.append((entry, *batch_info))
        else:
            per_ae_entries.append(entry)

    # {col_id: {ae_id: value}}
    col_results: dict[str, dict[str, Any]] = {}
    for cid in skip_ids:
        col_results[cid] = {aid: None for aid in ae_ids}
    for entry in per_ae_entries:
        col_results[entry.col_id] = {aid: None for aid in ae_ids}

    t_q = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit batch queries
        batch_futures = {
            executor.submit(_fetch_batch, sf, entry, soql, gf, ae_ids): entry
            for entry, soql, gf in batch_jobs
        }
        # Submit per-AE queries (SDR)
        per_ae_futures = {}
        for ae in ae_list:
            ae_params = {
                **params,
                "ae_user_id": ae["Id"],
                "ae_email": ae["Email"],
                "sdr_user_id": ae.get("SdrId") or _NULL_ID_SENTINEL,
            }
            for entry in per_ae_entries:
                fut = executor.submit(fetch_column, sf, entry, ae_params, overrides)
                per_ae_futures[fut] = (entry.col_id, ae["Id"])

        for fut in as_completed(batch_futures):
            col_id, mapping = fut.result()
            col_results[col_id] = mapping

        for fut in as_completed(per_ae_futures):
            col_id, ae_id = per_ae_futures[fut]
            _, val = fut.result()
            col_results[col_id][ae_id] = val

    n_per_ae = len(per_ae_entries) * len(ae_list)
    log.info("Queries: %d batch + %d per-AE (%.1fs)", len(batch_jobs), n_per_ae, time.time() - t_q)

    # Build DataFrame
    rows = []
    for ae in ae_list:
        aid = ae["Id"]
        row = {"AE Name": ae["Name"], "AE Email": ae["Email"], "AE Manager": ae.get("Manager", "")}
        for entry in ALL_COLUMNS:
            row[entry.col_id] = col_results.get(entry.col_id, {}).get(aid)
        c = row.get("S1-COL-C") or 0
        d = row.get("S1-COL-D") or 0
        f = row.get("S1-COL-F") or 0
        g = row.get("S1-COL-G") or 0
        row["S1-COL-E"] = (d / c) if c else None
        row["S1-COL-H"] = (g / f) if f else None
        rows.append(row)

    df = pd.DataFrame(rows)
    log.info("Dashboard: %d AEs, total %.1fs", len(rows), time.time() - t_start)
    return df


def get_managers_list(sf) -> list[str]:
    """Get distinct manager names for the Manager filter."""
    try:
        result = sf.query("""
            SELECT Id, Manager.Name
            FROM User
            WHERE IsActive = true
            AND ManagerId != null
            AND User_Role_Formula__c LIKE '%Sales Rep%'
            AND (NOT User_Role_Formula__c LIKE '%SDR%')
            AND (NOT User_Role_Formula__c LIKE '%Account%')
            ORDER BY Manager.Name
            LIMIT 500
        """)
        seen = set()
        managers = []
        for r in result.get("records", []):
            manager_obj = r.get("Manager")
            name = manager_obj.get("Name") if isinstance(manager_obj, dict) else None
            if name and name not in seen:
                seen.add(name)
                managers.append(name)
        return managers
    except Exception:
        return []


def get_ae_names_list(sf, manager_name: str | None = None) -> list[dict]:
    """Get AE names (optionally filtered by manager) for the AE Name filter."""
    where = ("WHERE IsActive = true"
             " AND User_Role_Formula__c LIKE '%Sales Rep%'"
             " AND (NOT User_Role_Formula__c LIKE '%SDR%')"
             " AND (NOT User_Role_Formula__c LIKE '%Account%')")
    if manager_name:
        where += f" AND Manager.Name = '{manager_name}'"
    try:
        result = sf.query(f"SELECT Id, Name, Email FROM User {where} ORDER BY Name LIMIT 200")
        return [
            {"id": r["Id"], "name": r["Name"], "email": r.get("Email", "")}
            for r in result.get("records", [])
        ]
    except Exception:
        return []
