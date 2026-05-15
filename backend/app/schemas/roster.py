from __future__ import annotations

from pydantic import BaseModel


class RosterEntryOut(BaseModel):
    sf_id: str
    name: str
    email: str
    manager_name: str
    manager_id: str
    sdr_id: str
    sdr_name: str
    sdr_email: str
    added_by: str
    added_at: str


class SfUserResult(BaseModel):
    sf_id: str
    name: str
    email: str
    manager_name: str
    manager_id: str
    sdr_id: str
    sdr_name: str
    sdr_email: str


class RosterImportResult(BaseModel):
    imported: int
