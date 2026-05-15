from __future__ import annotations

from pydantic import BaseModel


class SalesforceStatus(BaseModel):
    configured: bool
    has_token: bool
    instance_url: str | None = None
    issued_at: float | None = None
    age_seconds: float | None = None
    last_error: str | None = None
    last_success_at: float | None = None


class SalesforceRefreshResult(BaseModel):
    ok: bool
    instance_url: str | None = None
    latency_ms: int | None = None
    error: str | None = None


class SalesforceUserRoleSample(BaseModel):
    role_values: list[str]
    total_active_users: int
    error: str | None = None
