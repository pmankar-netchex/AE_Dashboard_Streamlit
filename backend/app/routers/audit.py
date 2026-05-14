from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user
from app.schemas.audit import AuditPage
from app.schemas.common import CurrentUser
from app.services.audit_service import get_audit_service

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditPage)
def list_audit(
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=50, ge=1, le=200),
    entity: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    _: CurrentUser = Depends(get_current_user),
) -> AuditPage:
    events, next_cursor = get_audit_service().list(
        cursor=cursor, page_size=page_size, entity=entity, actor=actor
    )
    return AuditPage(events=events, next_cursor=next_cursor)
