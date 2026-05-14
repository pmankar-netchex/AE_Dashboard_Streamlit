from __future__ import annotations

from pydantic import BaseModel


class AuditEvent(BaseModel):
    timestamp: str
    actor: str
    entity: str
    action: str
    target: str
    details: dict = {}


class AuditPage(BaseModel):
    events: list[AuditEvent]
    next_cursor: str | None = None
