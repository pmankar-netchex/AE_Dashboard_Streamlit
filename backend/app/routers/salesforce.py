from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.deps import get_current_user, require_admin
from app.schemas.common import CurrentUser
from app.schemas.salesforce import SalesforceRefreshResult, SalesforceStatus
from app.services.audit_service import get_audit_service
from app.services.salesforce_client import SalesforceAuthError, get_token_cache

router = APIRouter(prefix="/api/salesforce", tags=["salesforce"])


@router.get("/status", response_model=SalesforceStatus)
def status(_: CurrentUser = Depends(get_current_user)) -> SalesforceStatus:
    s = get_token_cache().status()
    return SalesforceStatus(
        configured=s.configured,
        has_token=s.has_token,
        instance_url=s.instance_url,
        issued_at=s.issued_at,
        age_seconds=s.age_seconds,
        last_error=s.last_error,
        last_success_at=s.last_success_at,
    )


@router.post("/refresh", response_model=SalesforceRefreshResult)
def refresh(user: CurrentUser = Depends(require_admin)) -> SalesforceRefreshResult:
    cache = get_token_cache()
    t0 = time.time()
    try:
        tok = cache.force_refresh()
        get_audit_service().write(
            actor=user.email,
            entity="salesforce",
            action="refresh",
            target=tok.instance_url,
        )
        return SalesforceRefreshResult(
            ok=True,
            instance_url=tok.instance_url,
            latency_ms=int((time.time() - t0) * 1000),
        )
    except SalesforceAuthError as exc:
        get_audit_service().write(
            actor=user.email,
            entity="salesforce",
            action="refresh-failed",
            details={"error": str(exc)},
        )
        return SalesforceRefreshResult(
            ok=False,
            latency_ms=int((time.time() - t0) * 1000),
            error=str(exc),
        )
