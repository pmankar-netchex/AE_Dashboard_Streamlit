from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Role = Literal["admin", "user"]


class UserOut(BaseModel):
    email: str
    role: Role
    is_active: bool
    added_by: str = ""
    added_at: str = ""


class UserCreateIn(BaseModel):
    email: str
    role: Role = "user"
    is_active: bool = True


class UserUpdateIn(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
