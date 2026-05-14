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
    # SOQL writes require BOTH the deployment-level ALLOW_PROD_QUERY_WRITES
    # flag AND the current user being an admin. Surfacing this in /api/me
    # means the UI doesn't show a Save button to non-admins that the
    # require_admin route dep would then 403 — single source of truth.
    flags = MeFlags(
        soql_writes_enabled=(
            user.role == "admin" and settings.allow_prod_query_writes
        ),
        scheduler_tz=settings.scheduler_tz,
    )
    return MeResponse(email=user.email, role=user.role, source=user.source, flags=flags)
