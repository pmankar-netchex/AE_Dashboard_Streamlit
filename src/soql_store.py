"""Persistent SOQL template storage.

Authoritative runtime source is an Azure Table Storage table keyed by col_id.
Falls back to a local JSON file when AZURE_STORAGE_CONNECTION_STRING is unset
(dev ergonomics). Every save also appends a history row for audit/rollback.

Callsites use load_overrides()/save_override() for backward compatibility.
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_LOCAL_FILE = Path(__file__).resolve().parent.parent / "soql_overrides.json"
_TABLE_QUERIES = "queries"
_TABLE_HISTORY = "querieshistory"
_PARTITION = "soql"

_service_cache = None


def _conn_str() -> Optional[str]:
    return os.environ.get("AZURE_STORAGE_CONNECTION_STRING")


def _table_client(table: str):
    """Return a TableClient for the given table, or None if unavailable."""
    global _service_cache
    conn = _conn_str()
    if not conn:
        return None
    try:
        from azure.data.tables import TableServiceClient
    except ImportError:
        log.warning("azure-data-tables not installed; using local-file fallback")
        return None
    if _service_cache is None:
        _service_cache = TableServiceClient.from_connection_string(conn)
    return _service_cache.get_table_client(table)


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
        log.warning("Table Storage load failed, falling back to local: %s", exc)
        return _load_local()


def save_query(col_id: str, template: str) -> None:
    """Upsert the active template and append a history row."""
    client = _table_client(_TABLE_QUERIES)
    if client is None:
        _save_local(col_id, template)
        return
    try:
        now = datetime.now(timezone.utc).isoformat()
        client.upsert_entity({
            "PartitionKey": _PARTITION,
            "RowKey": col_id,
            "Template": template,
            "UpdatedAt": now,
        })
        hist = _table_client(_TABLE_HISTORY)
        if hist is not None:
            hist.create_entity({
                "PartitionKey": col_id,
                "RowKey": now,
                "Template": template,
            })
    except Exception:
        log.exception("Table Storage save failed for %s", col_id)


def seed_missing(defaults: dict[str, str]) -> int:
    """Insert any col_id in defaults that isn't already in the table. Idempotent."""
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
        log.exception("seed_missing: failed to list existing rows")
        return 0
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for col_id, template in defaults.items():
        if col_id in existing or not template:
            continue
        try:
            client.create_entity({
                "PartitionKey": _PARTITION,
                "RowKey": col_id,
                "Template": template,
                "UpdatedAt": now,
                "Seeded": True,
            })
            n += 1
        except Exception:
            log.warning("seed_missing: create failed for %s (likely race)", col_id)
    return n


def _load_local() -> dict[str, str]:
    if not _LOCAL_FILE.exists():
        return {}
    try:
        return json.loads(_LOCAL_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("local overrides load failed: %s", e)
        return {}


def _save_local(col_id: str, template: str) -> None:
    current = _load_local()
    current[col_id] = template
    _LOCAL_FILE.write_text(json.dumps(current, indent=2))


def load_overrides() -> dict:
    return load_queries()


def save_override(col_id: str, soql: str) -> None:
    save_query(col_id, soql)
