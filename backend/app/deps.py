from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from app.auth.dev_identity import build_dev_user
from app.auth.principal import parse_x_ms_client_principal
from app.config import Settings, get_settings
from app.schemas.common import CurrentUser


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if settings.env == "dev":
        return build_dev_user(settings)

    header = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    claims = parse_x_ms_client_principal(header)
    if not claims:
        raise HTTPException(status_code=401, detail="missing or invalid principal")

    # Lazy import to avoid pulling storage on module load
    from app.services.user_service import get_user_service

    users = get_user_service()
    row = users.get(claims["email"])
    if not row or not row.is_active:
        raise HTTPException(status_code=403, detail="user not provisioned")

    return CurrentUser(
        email=row.email,
        role=row.role,
        oid=claims.get("oid"),
        source="entra",
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin required")
    return user
