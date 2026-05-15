from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from functools import lru_cache

from app.schemas.roster import RosterEntryOut
from app.storage.tables import TABLE_ROSTER, get_table_client

logger = logging.getLogger(__name__)

_PARTITION = "ae"


class RosterService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory: dict[str, dict] = {}

    def _client(self):
        return get_table_client(TABLE_ROSTER)

    def list(self) -> list[RosterEntryOut]:
        client = self._client()
        if client is None:
            with self._lock:
                rows = list(self._memory.values())
        else:
            try:
                rows = [dict(e) for e in client.query_entities(f"PartitionKey eq '{_PARTITION}'")]
            except Exception:
                logger.exception("roster list failed")
                return []
        return sorted(
            [self._to_out(r) for r in rows if r],
            key=lambda e: e.name.lower(),
        )

    def get(self, sf_id: str) -> RosterEntryOut | None:
        client = self._client()
        if client is None:
            with self._lock:
                row = self._memory.get(sf_id)
            return self._to_out(row) if row else None
        try:
            return self._to_out(dict(client.get_entity(_PARTITION, sf_id)))
        except Exception as exc:
            if "ResourceNotFound" in str(exc):
                return None
            raise

    def add(
        self,
        *,
        sf_id: str,
        name: str,
        email: str,
        manager_name: str,
        manager_id: str,
        sdr_id: str,
        sdr_name: str,
        sdr_email: str,
        actor: str,
    ) -> RosterEntryOut:
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "PartitionKey": _PARTITION,
            "RowKey": sf_id,
            "Name": name,
            "Email": email,
            "ManagerName": manager_name,
            "ManagerId": manager_id,
            "SdrId": sdr_id,
            "SdrName": sdr_name,
            "SdrEmail": sdr_email,
            "AddedBy": actor,
            "AddedAt": now,
        }
        client = self._client()
        if client is None:
            with self._lock:
                self._memory[sf_id] = row
        else:
            client.upsert_entity(row)
        return self._to_out(row)

    def remove(self, sf_id: str) -> bool:
        client = self._client()
        if client is None:
            with self._lock:
                return self._memory.pop(sf_id, None) is not None
        try:
            client.delete_entity(_PARTITION, sf_id)
            return True
        except Exception as exc:
            if "ResourceNotFound" in str(exc):
                return False
            raise

    def bulk_import(self, entries: list[dict], actor: str) -> int:
        count = 0
        for e in entries:
            self.add(
                sf_id=e["sf_id"],
                name=e["name"],
                email=e["email"],
                manager_name=e.get("manager_name", ""),
                manager_id=e.get("manager_id", ""),
                sdr_id=e.get("sdr_id", ""),
                sdr_name=e.get("sdr_name", ""),
                sdr_email=e.get("sdr_email", ""),
                actor=actor,
            )
            count += 1
        return count

    def is_empty(self) -> bool:
        """True when no entries exist — used to decide whether to fall back to live SF query."""
        client = self._client()
        if client is None:
            with self._lock:
                return not bool(self._memory)
        try:
            for _ in client.query_entities(
                f"PartitionKey eq '{_PARTITION}'", results_per_page=1
            ):
                return False
            return True
        except Exception:
            return True

    @staticmethod
    def _to_out(row: dict | None) -> RosterEntryOut | None:
        if not row:
            return None
        return RosterEntryOut(
            sf_id=str(row.get("RowKey") or ""),
            name=str(row.get("Name") or ""),
            email=str(row.get("Email") or ""),
            manager_name=str(row.get("ManagerName") or ""),
            manager_id=str(row.get("ManagerId") or ""),
            sdr_id=str(row.get("SdrId") or ""),
            sdr_name=str(row.get("SdrName") or ""),
            sdr_email=str(row.get("SdrEmail") or ""),
            added_by=str(row.get("AddedBy") or ""),
            added_at=str(row.get("AddedAt") or ""),
        )


@lru_cache
def get_roster_service() -> RosterService:
    return RosterService()


def reset_roster_service() -> None:
    get_roster_service.cache_clear()
