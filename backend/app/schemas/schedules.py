from __future__ import annotations

from pydantic import BaseModel


class ScheduleOut(BaseModel):
    id: str
    name: str
    cron: str
    recipients: list[str]
    subject: str
    filters: dict
    is_active: bool
    created_by: str
    created_at: str
    last_run_at: str | None = None
    last_run_status: str | None = None


class ScheduleCreateIn(BaseModel):
    name: str
    cron: str
    recipients: list[str]
    subject: str = "AE Performance — All Source Summary"
    filters: dict = {}
    is_active: bool = True


class ScheduleUpdateIn(BaseModel):
    name: str | None = None
    cron: str | None = None
    recipients: list[str] | None = None
    subject: str | None = None
    filters: dict | None = None
    is_active: bool | None = None


class SendNowResult(BaseModel):
    ok: bool
    message_id: str = ""
    error: str | None = None


class SendOnceIn(BaseModel):
    recipients: list[str]
    subject: str = "AE Performance — All Source Summary"
    filters: dict = {}
