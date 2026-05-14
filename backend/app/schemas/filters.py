from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

TimePreset = Literal["this_week", "last_week", "this_month", "last_month", "custom"]


class ManagerOption(BaseModel):
    name: str


class AEOption(BaseModel):
    id: str
    name: str
    email: str
    manager: str | None = None


class TimePresetOption(BaseModel):
    key: TimePreset
    display_name: str
