from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user, require_admin
from app.legacy import soql_store
from app.legacy.time_filters import build_filter_params, resolve_time_period
from app.schemas.common import CurrentUser
from app.schemas.soql import (
    SoqlEntryOut,
    SoqlHistoryRow,
    SoqlTestRequest,
    SoqlTestResult,
    SoqlUpdateIn,
)
from app.services import soql_service
from app.services.audit_service import get_audit_service
from app.services.salesforce_client import get_sf_client

router = APIRouter(prefix="/api/soql", tags=["soql"])


@router.get("", response_model=list[SoqlEntryOut])
def list_all(_: CurrentUser = Depends(get_current_user)) -> list[SoqlEntryOut]:
    return soql_service.list_entries()


@router.get("/{col_id}", response_model=SoqlEntryOut)
def get_one(col_id: str, _: CurrentUser = Depends(get_current_user)) -> SoqlEntryOut:
    entry = soql_service.get_entry(col_id)
    if entry is None:
        raise HTTPException(404, detail=f"unknown col_id: {col_id}")
    return entry


@router.put("/{col_id}", response_model=SoqlEntryOut)
def update_one(
    col_id: str, body: SoqlUpdateIn, user: CurrentUser = Depends(require_admin)
) -> SoqlEntryOut:
    try:
        soql_service.update_entry(col_id, body.template, actor=user.email)
    except KeyError:
        raise HTTPException(404, detail=f"unknown col_id: {col_id}")
    except soql_store.SoqlWriteForbidden as exc:
        raise HTTPException(status_code=423, detail=str(exc))
    get_audit_service().write(
        actor=user.email, entity="soql", action="update", target=col_id
    )
    entry = soql_service.get_entry(col_id)
    assert entry is not None
    return entry


@router.post("/{col_id}/test", response_model=SoqlTestResult)
def test_one(
    col_id: str, body: SoqlTestRequest, user: CurrentUser = Depends(require_admin)
) -> SoqlTestResult:
    start, end = resolve_time_period(body.period, None, None)
    params = build_filter_params(
        ae_user_id=body.ae_user_id,
        ae_email=None,
        manager_name=None,
        time_start=start,
        time_end=end,
    )
    sf = get_sf_client()
    return soql_service.test_query(sf, col_id, body.template, params)


@router.get("/{col_id}/history", response_model=list[SoqlHistoryRow])
def get_history(
    col_id: str, _: CurrentUser = Depends(get_current_user)
) -> list[SoqlHistoryRow]:
    return soql_service.history(col_id)
