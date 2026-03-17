"""
Data Engine — executes SOQL registry queries, builds unified DataFrame.
[spec: Steps 3–5, Critical Rule #3]

Per-SOQL error isolation: if one query fails, only its column shows NaN.
"""
from __future__ import annotations
import pandas as pd
from typing import Any

from src.soql_registry import ALL_COLUMNS, COLUMN_BY_ID, build_query, SOQLEntry
from src.meta_filters import build_filter_params


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


def fetch_column(sf, entry: SOQLEntry, params: dict) -> tuple[str, Any]:
    """
    Execute one SOQL entry and return (col_id, value).
    On failure returns (col_id, None) — per-SOQL error isolation.
    """
    if entry.computed or entry.blocked:
        return entry.col_id, None
    soql = build_query(entry, params)
    try:
        val = _run_query(sf, soql)
        return entry.col_id, val
    except Exception:
        return entry.col_id, None


def fetch_all_columns(sf, params: dict) -> dict[str, Any]:
    """
    Run every non-computed, non-blocked SOQL and return {col_id: value}.
    Per-query error isolation: failures become None for that column only.
    """
    results: dict[str, Any] = {}
    for entry in ALL_COLUMNS:
        col_id, val = fetch_column(sf, entry, params)
        results[col_id] = val

    # Compute derived columns [spec: S1-COL-E = D/C, S1-COL-H = G/F]
    c = results.get("S1-COL-C") or 0
    d = results.get("S1-COL-D") or 0
    f = results.get("S1-COL-F") or 0
    g = results.get("S1-COL-G") or 0
    results["S1-COL-E"] = (d / c) if c else None
    results["S1-COL-H"] = (g / f) if f else None

    return results


def build_ae_list(sf, params: dict) -> list[dict]:
    """
    Get the list of AEs to display based on manager/ae_user_id filter.
    Returns list of {Id, Name, Email} dicts.
    """
    if params.get("ae_user_id"):
        query = f"""
            SELECT Id, Name, Email
            FROM User
            WHERE Id = '{params["ae_user_id"]}'
            AND IsActive = true
        """
    elif params.get("manager_name"):
        query = f"""
            SELECT Id, Name, Email
            FROM User
            WHERE Manager.Name = '{params["manager_name"]}'
            AND IsActive = true
            ORDER BY Name
        """
    else:
        query = """
            SELECT Id, Name, Email
            FROM User
            WHERE IsActive = true
            AND UserRole.Name LIKE '%Sales Rep%'
            ORDER BY Name
            LIMIT 200
        """
    try:
        result = sf.query(query)
        return [
            {"Id": r["Id"], "Name": r["Name"], "Email": r.get("Email", "")}
            for r in result.get("records", [])
        ]
    except Exception:
        return []


def build_dashboard_dataframe(sf, params: dict) -> pd.DataFrame:
    """
    Build the unified DataFrame with one row per AE and columns C–AD.
    [spec: Step 5]
    """
    ae_list = build_ae_list(sf, params)
    if not ae_list:
        return pd.DataFrame()

    rows = []
    for ae in ae_list:
        ae_params = {
            **params,
            "ae_user_id": ae["Id"],
            "ae_email": ae["Email"],
        }
        col_values = fetch_all_columns(sf, ae_params)
        row = {"AE Name": ae["Name"], "AE Email": ae["Email"]}
        for entry in ALL_COLUMNS:
            row[entry.col_id] = col_values.get(entry.col_id)
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def get_managers_list(sf) -> list[str]:
    """Get distinct manager names for the Manager filter."""
    try:
        result = sf.query("""
            SELECT Manager.Name mgr
            FROM User
            WHERE IsActive = true
            AND Manager.Name != null
            AND UserRole.Name LIKE '%Sales Rep%'
            ORDER BY Manager.Name
        """)
        seen = set()
        managers = []
        for r in result.get("records", []):
            name = r.get("mgr")
            if name and name not in seen:
                seen.add(name)
                managers.append(name)
        return managers
    except Exception:
        return []


def get_ae_names_list(sf, manager_name: str | None = None) -> list[dict]:
    """Get AE names (optionally filtered by manager) for the AE Name filter."""
    where = "WHERE IsActive = true AND UserRole.Name LIKE '%Sales Rep%'"
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
