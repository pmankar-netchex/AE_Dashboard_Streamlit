from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache

from app.schemas.audit import AuditEvent
from app.storage.tables import TABLE_AUDIT, get_table_client

logger = logging.getLogger(__name__)

_PARTITION = "audit"
# Reverse-epoch ordering so newest events sort first as ASCII strings.
_MAX = 9_999_999_999.999


def _rowkey(now: float | None = None) -> str:
    t = now if now is not None else time.time()
    return f"{_MAX - t:020.3f}-{uuid.uuid4().hex[:8]}"


class AuditService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory: list[AuditEvent] = []

    def _client(self):
        return get_table_client(TABLE_AUDIT)

    def write(
        self,
        *,
        actor: str,
        entity: str,
        action: str,
        target: str = "",
        details: dict | None = None,
    ) -> AuditEvent:
        now = time.time()
        iso = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
        event = AuditEvent(
            timestamp=iso,
            actor=actor or "",
            entity=entity,
            action=action,
            target=target,
            details=details or {},
        )
        client = self._client()
        if client is None:
            with self._lock:
                self._memory.append(event)
                self._memory.sort(key=lambda e: e.timestamp, reverse=True)
                self._memory = self._memory[:1000]
            return event
        try:
            client.create_entity(
                {
                    "PartitionKey": _PARTITION,
                    "RowKey": _rowkey(now),
                    "Timestamp": iso,
                    "Actor": actor or "",
                    "Entity": entity,
                    "Action": action,
                    "Target": target,
                    "Details": json.dumps(details or {}),
                }
            )
        except Exception:
            logger.exception("audit write failed (entity=%s action=%s)", entity, action)
        return event

    def list(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 50,
        entity: str | None = None,
        actor: str | None = None,
    ) -> tuple[list[AuditEvent], str | None]:
        page_size = max(1, min(page_size, 200))
        client = self._client()
        if client is None:
            with self._lock:
                rows = list(self._memory)
            if entity:
                rows = [r for r in rows if r.entity == entity]
            if actor:
                rows = [r for r in rows if r.actor == actor]
            try:
                start = int(cursor) if cursor else 0
            except ValueError:
                start = 0
            slice_ = rows[start : start + page_size]
            next_cursor = (
                str(start + page_size) if (start + page_size) < len(rows) else None
            )
            return slice_, next_cursor

        # Azure path
        filter_parts = [f"PartitionKey eq '{_PARTITION}'"]
        if entity:
            filter_parts.append(f"Entity eq '{entity}'")
        if actor:
            filter_parts.append(f"Actor eq '{actor}'")
        filter_expr = " and ".join(filter_parts)
        try:
            iterator = client.query_entities(
                filter_expr,
                results_per_page=page_size,
            )
            page = next(iterator.by_page(continuation_token=cursor or None))
            entities = list(page)
            next_cursor = iterator.continuation_token
            events = [
                AuditEvent(
                    timestamp=str(e.get("Timestamp") or ""),
                    actor=str(e.get("Actor") or ""),
                    entity=str(e.get("Entity") or ""),
                    action=str(e.get("Action") or ""),
                    target=str(e.get("Target") or ""),
                    details=_safe_json(e.get("Details")),
                )
                for e in entities
            ]
            return events, next_cursor
        except Exception:
            logger.exception("audit list failed")
            return [], None


def _safe_json(raw) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"raw": str(raw)}


@lru_cache
def get_audit_service() -> AuditService:
    return AuditService()


def reset_audit_service() -> None:
    get_audit_service.cache_clear()
