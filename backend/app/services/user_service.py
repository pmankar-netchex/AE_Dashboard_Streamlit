from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Literal

from app.storage.tables import TABLE_USERS, get_table_client

logger = logging.getLogger(__name__)

Role = Literal["admin", "user"]
_PARTITION = "user"


@dataclass
class UserRow:
    email: str
    role: Role
    is_active: bool = True
    added_by: str = ""
    added_at: str = ""

    @classmethod
    def from_entity(cls, e: dict) -> "UserRow":
        return cls(
            email=str(e.get("Email") or e["RowKey"]).lower(),
            role=("admin" if e.get("Role") == "admin" else "user"),
            is_active=bool(e.get("IsActive", True)),
            added_by=str(e.get("AddedBy") or ""),
            added_at=str(e.get("AddedAt") or ""),
        )

    def to_entity(self) -> dict:
        return {
            "PartitionKey": _PARTITION,
            "RowKey": self.email,
            "Email": self.email,
            "Role": self.role,
            "IsActive": self.is_active,
            "AddedBy": self.added_by,
            "AddedAt": self.added_at,
        }


class UserService:
    """Users table CRUD. Backed by Azure Table Storage in prod, in-memory in dev."""

    def __init__(self) -> None:
        self._memory: dict[str, UserRow] = {}

    def _client(self):
        return get_table_client(TABLE_USERS)

    def get(self, email: str) -> UserRow | None:
        key = email.strip().lower()
        if not key:
            return None
        client = self._client()
        if client is None:
            return self._memory.get(key)
        try:
            e = client.get_entity(partition_key=_PARTITION, row_key=key)
            return UserRow.from_entity(dict(e))
        except Exception as exc:
            if "ResourceNotFound" in str(exc) or "not found" in str(exc).lower():
                return None
            logger.exception("UserService.get(%s) failed", key)
            return None

    def list(self) -> list[UserRow]:
        client = self._client()
        if client is None:
            return sorted(self._memory.values(), key=lambda u: u.email)
        try:
            rows = [
                UserRow.from_entity(dict(e))
                for e in client.query_entities(f"PartitionKey eq '{_PARTITION}'")
            ]
            rows.sort(key=lambda u: u.email)
            return rows
        except Exception:
            logger.exception("UserService.list failed")
            return []

    def upsert(self, row: UserRow, actor: str) -> UserRow:
        email = row.email.strip().lower()
        if not email:
            raise ValueError("email is required")
        existing = self.get(email)
        out = UserRow(
            email=email,
            role=row.role,
            is_active=row.is_active,
            added_by=(existing.added_by if existing else (actor or row.added_by)),
            added_at=(
                existing.added_at
                if existing
                else (row.added_at or datetime.now(timezone.utc).isoformat())
            ),
        )
        client = self._client()
        if client is None:
            self._memory[email] = out
            return out
        client.upsert_entity(out.to_entity())
        return out

    def delete(self, email: str, actor: str) -> bool:
        key = email.strip().lower()
        client = self._client()
        if client is None:
            return self._memory.pop(key, None) is not None
        try:
            client.delete_entity(partition_key=_PARTITION, row_key=key)
            return True
        except Exception as exc:
            if "ResourceNotFound" in str(exc):
                return False
            logger.exception("UserService.delete(%s) failed", key)
            raise


@lru_cache
def get_user_service() -> UserService:
    return UserService()


def reset_user_service_cache() -> None:
    """Test helper — clears the cached UserService singleton."""
    get_user_service.cache_clear()
