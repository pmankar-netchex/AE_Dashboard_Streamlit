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


class SalesforceUserInfoProbe(BaseModel):
    """Result of hitting /services/oauth2/userinfo with the cached token.

    Distinguishes "the /oauth2/token endpoint mints a token successfully" from
    "Salesforce accepts that token for an authenticated REST call" — these
    diverge when the Connected App's Run-As user is missing or inactive.
    """

    ok: bool
    status_code: int | None = None
    user_id: str | None = None
    username: str | None = None
    email: str | None = None
    display_name: str | None = None
    organization_id: str | None = None
    instance_url: str | None = None
    latency_ms: int | None = None
    error: str | None = None
