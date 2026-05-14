from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.schemas.common import CurrentUser
from app.services.column_meta import column_meta_payload

router = APIRouter(prefix="/api", tags=["columns"])


@router.get("/columns")
def get_columns(_: CurrentUser = Depends(get_current_user)) -> dict:
    """Column registry + section + KPI metadata for the React UI."""
    return column_meta_payload()
