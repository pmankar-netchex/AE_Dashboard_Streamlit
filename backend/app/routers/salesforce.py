from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.deps import get_current_user, require_admin
from app.schemas.common import CurrentUser
from app.schemas.salesforce import (
    SalesforceRefreshResult,
    SalesforceStatus,
    SalesforceUserInfoProbe,
    SalesforceUserRoleSample,
)
from app.services.audit_service import get_audit_service
from app.services.salesforce_client import (
    SalesforceAuthError,
    get_sf_client,
    get_token_cache,
    probe_userinfo,
)

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
        token_origin=s.token_origin,
        token_origin_is_generic=s.token_origin_is_generic,
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


@router.get("/userinfo", response_model=SalesforceUserInfoProbe)
def userinfo_probe(
    _: CurrentUser = Depends(require_admin),
) -> SalesforceUserInfoProbe:
    """Hit /services/oauth2/userinfo to verify the cached token actually
    authenticates (separate from minting). Identifies the Connected App's
    Run-As user — the smoking gun when CC-flow tokens mint OK but fail REST.
    """
    result = probe_userinfo(get_token_cache())
    return SalesforceUserInfoProbe(**result)


@router.get("/user-roles", response_model=SalesforceUserRoleSample)
def user_role_sample(_: CurrentUser = Depends(require_admin)) -> SalesforceUserRoleSample:
    """Return distinct User_Role_Formula__c values from active users. Admin-only diagnostic."""
    sf = get_sf_client()
    try:
        count_result = sf.query("SELECT COUNT() FROM User WHERE IsActive = true")
        total = count_result.get("totalSize", 0)

        result = sf.query(
            "SELECT User_Role_Formula__c FROM User WHERE IsActive = true LIMIT 200"
        )
        seen: set[str] = set()
        for r in result.get("records", []):
            val = r.get("User_Role_Formula__c")
            if val:
                seen.add(str(val))
        return SalesforceUserRoleSample(
            role_values=sorted(seen),
            total_active_users=total,
        )
    except Exception as exc:
        return SalesforceUserRoleSample(
            role_values=[],
            total_active_users=0,
            error=str(exc),
        )
