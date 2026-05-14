from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from functools import lru_cache

from apscheduler.triggers.cron import CronTrigger

from app.schemas.schedules import ScheduleOut
from app.storage.tables import TABLE_SCHEDULES, get_table_client

logger = logging.getLogger(__name__)

_PARTITION = "schedule"


class ScheduleService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory: dict[str, dict] = {}

    def _client(self):
        return get_table_client(TABLE_SCHEDULES)

    # ---- CRUD ----

    def list(self) -> list[ScheduleOut]:
        client = self._client()
        if client is None:
            with self._lock:
                return [self._row_to_out(r) for r in self._memory.values()]
        try:
            return sorted(
                [
                    self._row_to_out(dict(e))
                    for e in client.query_entities(f"PartitionKey eq '{_PARTITION}'")
                ],
                key=lambda s: s.created_at,
                reverse=True,
            )
        except Exception:
            logger.exception("schedule list failed")
            return []

    def get(self, schedule_id: str) -> ScheduleOut | None:
        client = self._client()
        if client is None:
            with self._lock:
                row = self._memory.get(schedule_id)
            return self._row_to_out(row) if row else None
        try:
            e = dict(client.get_entity(_PARTITION, schedule_id))
            return self._row_to_out(e)
        except Exception as exc:
            if "ResourceNotFound" in str(exc):
                return None
            raise

    def create(
        self,
        *,
        name: str,
        cron: str,
        recipients: list[str],
        subject: str,
        filters: dict,
        is_active: bool,
        actor: str,
    ) -> ScheduleOut:
        # Validate cron
        CronTrigger.from_crontab(cron)
        sid = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "PartitionKey": _PARTITION,
            "RowKey": sid,
            "Name": name,
            "Cron": cron,
            "Recipients": json.dumps(recipients),
            "Subject": subject,
            "Filters": json.dumps(filters),
            "IsActive": bool(is_active),
            "CreatedBy": actor,
            "CreatedAt": now,
            "LastRunAt": "",
            "LastRunStatus": "",
        }
        client = self._client()
        if client is None:
            with self._lock:
                self._memory[sid] = row
        else:
            client.create_entity(row)
        return self._row_to_out(row)

    def update(self, schedule_id: str, **patch) -> ScheduleOut | None:
        existing = self._raw(schedule_id)
        if existing is None:
            return None
        if "cron" in patch and patch["cron"] is not None:
            CronTrigger.from_crontab(patch["cron"])
        merged = dict(existing)
        if "name" in patch and patch["name"] is not None:
            merged["Name"] = patch["name"]
        if "cron" in patch and patch["cron"] is not None:
            merged["Cron"] = patch["cron"]
        if "recipients" in patch and patch["recipients"] is not None:
            merged["Recipients"] = json.dumps(patch["recipients"])
        if "subject" in patch and patch["subject"] is not None:
            merged["Subject"] = patch["subject"]
        if "filters" in patch and patch["filters"] is not None:
            merged["Filters"] = json.dumps(patch["filters"])
        if "is_active" in patch and patch["is_active"] is not None:
            merged["IsActive"] = bool(patch["is_active"])
        client = self._client()
        if client is None:
            with self._lock:
                self._memory[schedule_id] = merged
        else:
            client.upsert_entity(merged)
        return self._row_to_out(merged)

    def delete(self, schedule_id: str) -> bool:
        client = self._client()
        if client is None:
            with self._lock:
                return self._memory.pop(schedule_id, None) is not None
        try:
            client.delete_entity(_PARTITION, schedule_id)
            return True
        except Exception as exc:
            if "ResourceNotFound" in str(exc):
                return False
            raise

    def record_run(
        self, schedule_id: str, *, ok: bool, message: str = ""
    ) -> None:
        existing = self._raw(schedule_id)
        if not existing:
            return
        existing["LastRunAt"] = datetime.now(timezone.utc).isoformat()
        existing["LastRunStatus"] = "ok" if ok else f"error: {message[:200]}"
        client = self._client()
        if client is None:
            with self._lock:
                self._memory[schedule_id] = existing
        else:
            try:
                client.upsert_entity(existing)
            except Exception:
                logger.exception("record_run upsert failed")

    # ---- internals ----

    def _raw(self, schedule_id: str) -> dict | None:
        client = self._client()
        if client is None:
            with self._lock:
                return dict(self._memory.get(schedule_id) or {}) or None
        try:
            return dict(client.get_entity(_PARTITION, schedule_id))
        except Exception:
            return None

    @staticmethod
    def _row_to_out(row: dict | None) -> ScheduleOut | None:
        if not row:
            return None
        return ScheduleOut(
            id=row["RowKey"],
            name=str(row.get("Name") or ""),
            cron=str(row.get("Cron") or ""),
            recipients=_safe_list(row.get("Recipients")),
            subject=str(row.get("Subject") or ""),
            filters=_safe_dict(row.get("Filters")),
            is_active=bool(row.get("IsActive", True)),
            created_by=str(row.get("CreatedBy") or ""),
            created_at=str(row.get("CreatedAt") or ""),
            last_run_at=str(row.get("LastRunAt") or "") or None,
            last_run_status=str(row.get("LastRunStatus") or "") or None,
        )


def _safe_list(raw) -> list[str]:
    if not raw:
        return []
    try:
        v = json.loads(raw)
        return [str(x) for x in v if x]
    except Exception:
        return []


def _safe_dict(raw) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


@lru_cache
def get_schedule_service() -> ScheduleService:
    return ScheduleService()


def reset_schedule_service() -> None:
    get_schedule_service.cache_clear()
