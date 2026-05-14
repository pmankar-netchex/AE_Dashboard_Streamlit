from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Table names — single source of truth.
TABLE_QUERIES = "queries"
TABLE_HISTORY = "querieshistory"
TABLE_USERS = "users"
TABLE_SCHEDULES = "schedules"
TABLE_AUDIT = "audit"
TABLE_JOBSTORE = "jobstore"

ALL_TABLES = [
    TABLE_QUERIES,
    TABLE_HISTORY,
    TABLE_USERS,
    TABLE_SCHEDULES,
    TABLE_AUDIT,
    TABLE_JOBSTORE,
]

_service_cache = None
_service_lock = threading.Lock()


def _conn_string() -> Optional[str]:
    from app.config import get_settings

    return get_settings().azure_storage_connection_string or None


def reset_service_cache() -> None:
    """Test helper — clears the cached TableServiceClient singleton."""
    global _service_cache
    with _service_lock:
        _service_cache = None


def get_service():
    """Return the TableServiceClient singleton, or None if unconfigured."""
    global _service_cache
    if _service_cache is not None:
        return _service_cache
    conn = _conn_string()
    if not conn:
        return None
    try:
        from azure.data.tables import TableServiceClient
    except ImportError:
        logger.warning("azure-data-tables not installed")
        return None
    with _service_lock:
        if _service_cache is None:
            _service_cache = TableServiceClient.from_connection_string(conn)
    return _service_cache


def get_table_client(table_name: str):
    """Return a TableClient for the given table, or None if unconfigured."""
    svc = get_service()
    if svc is None:
        return None
    return svc.get_table_client(table_name)
