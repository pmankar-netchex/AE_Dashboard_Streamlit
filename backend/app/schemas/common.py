from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


Role = Literal["admin", "user"]


class CurrentUser(BaseModel):
    email: str
    role: Role
    oid: str | None = None
    source: Literal["dev", "entra"] = "dev"


class MeFlags(BaseModel):
    soql_writes_enabled: bool = False
    scheduler_tz: str = "America/Chicago"


class MeResponse(BaseModel):
    email: str
    role: Role
    source: Literal["dev", "entra"]
    flags: MeFlags
