from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import get_current_user
from app.schemas.common import CurrentUser, MeFlags, MeResponse

router = APIRouter(prefix="/api", tags=["me"])


@router.get("/me", response_model=MeResponse)
def me(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> MeResponse:
    flags = MeFlags(soql_writes_enabled=settings.allow_prod_query_writes)
    return MeResponse(email=user.email, role=user.role, source=user.source, flags=flags)
