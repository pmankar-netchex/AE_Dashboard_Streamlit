"""Persistent SOQL template storage.

Authoritative runtime source is an Azure Table Storage table keyed by col_id.
Falls back to a local JSON file when AZURE_STORAGE_CONNECTION_STRING is unset
(dev ergonomics). Every save also appends a history row for audit/rollback.

Write protection: when Azure Table Storage is the active backend, mutations
require ALLOW_PROD_QUERY_WRITES=true. Local-file fallback (dev only) is
unguarded by design.

Ported from src/soql_store.py with write-gate, history loader, and updated
module paths.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Repo-root-relative local fallback (backend/app/legacy/soql_store.py → 3 parents up)
_LOCAL_FILE = Path(__file__).resolve().parents[3] / "soql_overrides.json"
_TABLE_QUERIES = "queries"
_TABLE_HISTORY = "querieshistory"
_PARTITION = "soql"


class SoqlWriteForbidden(Exception):
    """Raised when a write is attempted against prod Table Storage without ALLOW_PROD_QUERY_WRITES."""


# ---- backend selection ----


def _conn_str() -> Optional[str]:
    return os.environ.get("AZURE_STORAGE_CONNECTION_STRING") or None


def _writes_enabled() -> bool:
    raw = os.environ.get("ALLOW_PROD_QUERY_WRITES", "")
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _table_client(table: str):
    """Return a TableClient for the given table, or None if unavailable."""
    if not _conn_str():
        return None
    # Reuse the storage layer's singleton when running inside the FastAPI app.
    try:
        from app.storage.tables import get_table_client

        return get_table_client(table)
    except ImportError:
        pass
    try:
        from azure.data.tables import TableServiceClient
    except ImportError:
        logger.warning("azure-data-tables not installed; using local-file fallback")
        return None
    return TableServiceClient.from_connection_string(_conn_str()).get_table_client(table)


# ---- reads ----


def load_queries() -> dict[str, str]:
    """Return {col_id: template} from Table Storage, or local file fallback."""
    client = _table_client(_TABLE_QUERIES)
    if client is None:
        return _load_local()
    try:
        out: dict[str, str] = {}
        for e in client.query_entities(f"PartitionKey eq '{_PARTITION}'"):
            out[e["RowKey"]] = e.get("Template", "")
        return out
    except Exception as exc:
        logger.warning("Table Storage load failed, falling back to local: %s", exc)
        return _load_local()


def load_history(col_id: str, limit: int = 25) -> list[dict[str, Any]]:
    """Return up to `limit` recent history rows for col_id, newest first."""
    client = _table_client(_TABLE_HISTORY)
    if client is None:
        return []
    try:
        rows = [
            {
                "version": e["RowKey"],
                "template": e.get("Template", ""),
                "saved_by": e.get("SavedBy", ""),
                "saved_at": e.get("RowKey", ""),
            }
            for e in client.query_entities(f"PartitionKey eq '{col_id}'")
        ]
        rows.sort(key=lambda r: r["version"], reverse=True)
        return rows[:limit]
    except Exception:
        logger.exception("load_history(%s) failed", col_id)
        return []


# ---- writes (gated when Table Storage backend is active) ----


def save_query(col_id: str, template: str, actor: str = "") -> None:
    """Upsert the active template and append a history row.

    Raises SoqlWriteForbidden when Table Storage is active and
    ALLOW_PROD_QUERY_WRITES is not set to a truthy value. Local-file fallback
    is unguarded (dev-only path).
    """
    if _conn_str() and not _writes_enabled():
        raise SoqlWriteForbidden(
            "Writes to production SOQL store are disabled. "
            "Set ALLOW_PROD_QUERY_WRITES=true to enable."
        )
    client = _table_client(_TABLE_QUERIES)
    if client is None:
        _save_local(col_id, template)
        return
    now = datetime.now(timezone.utc).isoformat()
    client.upsert_entity(
        {
            "PartitionKey": _PARTITION,
            "RowKey": col_id,
            "Template": template,
            "UpdatedAt": now,
            "UpdatedBy": actor,
        }
    )
    hist = _table_client(_TABLE_HISTORY)
    if hist is not None:
        try:
            hist.create_entity(
                {
                    "PartitionKey": col_id,
                    "RowKey": now,
                    "Template": template,
                    "SavedBy": actor,
                }
            )
        except Exception:
            logger.warning("history append failed for %s (likely race)", col_id)


def seed_missing(defaults: dict[str, str]) -> int:
    """Insert any col_id in defaults that isn't already in the table. Idempotent.

    Subject to the same write-gate as save_query when Table Storage is active.
    """
    if _conn_str() and not _writes_enabled():
        # Silent no-op for seed in prod-locked mode — admins seed via scripts/sync_queries.py
        return 0
    client = _table_client(_TABLE_QUERIES)
    if client is None:
        return 0
    try:
        existing = {
            e["RowKey"]
            for e in client.query_entities(
                f"PartitionKey eq '{_PARTITION}'", select=["RowKey"]
            )
        }
    except Exception:
        logger.exception("seed_missing: failed to list existing rows")
        return 0
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for col_id, template in defaults.items():
        if col_id in existing or not template:
            continue
        try:
            client.create_entity(
                {
                    "PartitionKey": _PARTITION,
                    "RowKey": col_id,
                    "Template": template,
                    "UpdatedAt": now,
                    "Seeded": True,
                }
            )
            n += 1
        except Exception:
            logger.warning("seed_missing: create failed for %s (likely race)", col_id)
    return n


# ---- local fallback ----


def _load_local() -> dict[str, str]:
    if not _LOCAL_FILE.exists():
        return {}
    try:
        return json.loads(_LOCAL_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("local overrides load failed: %s", e)
        return {}


def _save_local(col_id: str, template: str) -> None:
    current = _load_local()
    current[col_id] = template
    _LOCAL_FILE.write_text(json.dumps(current, indent=2))


# ---- back-compat aliases retained for callers ----


def load_overrides() -> dict:
    return load_queries()


def save_override(col_id: str, soql: str, actor: str = "") -> None:
    save_query(col_id, soql, actor=actor)
