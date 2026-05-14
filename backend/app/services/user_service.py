from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal


@dataclass
class UserRow:
    email: str
    role: Literal["admin", "user"]
    is_active: bool = True
    added_by: str = ""
    added_at: str = ""


class UserService:
    """Stub user service. Real implementation lands in M2 against Azure Table Storage."""

    def get(self, email: str) -> UserRow | None:
        return None

    def list(self) -> list[UserRow]:
        return []

    def upsert(self, row: UserRow, actor: str) -> UserRow:
        return row

    def delete(self, email: str, actor: str) -> None:
        return None


@lru_cache
def get_user_service() -> UserService:
    return UserService()
