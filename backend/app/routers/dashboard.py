from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user
from app.schemas.common import CurrentUser
from app.schemas.dashboard import AEDrillDownResponse, DashboardResponse
from app.services.dashboard_service import (
    fetch_ae_drilldown,
    fetch_dashboard,
    resolve_filter_params,
)
from app.services.salesforce_client import SalesforceAuthError, get_sf_client

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    manager: str | None = Query(default=None),
    ae_id: str | None = Query(default=None, alias="ae"),
    ae_email: str | None = Query(default=None),
    period: str | None = Query(default="this_month"),
    custom_start: date | None = Query(default=None, alias="from"),
    custom_end: date | None = Query(default=None, alias="to"),
    _: CurrentUser = Depends(get_current_user),
) -> DashboardResponse:
    params, start, end = resolve_filter_params(
        manager=manager,
        ae_user_id=ae_id,
        ae_email=ae_email,
        period=period,
        custom_start=custom_start,
        custom_end=custom_end,
    )
    sf = get_sf_client()
    try:
        return fetch_dashboard(sf, params, start, end)
    except SalesforceAuthError as exc:
        log.error("Salesforce auth error: %s", exc)
        raise HTTPException(status_code=503, detail=f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        log.exception("Dashboard fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Salesforce query failed: {exc}")


@router.get("/ae/{ae_id}", response_model=AEDrillDownResponse)
def get_ae_drilldown(
    ae_id: str,
    manager: str | None = Query(default=None),
    period: str | None = Query(default="this_month"),
    custom_start: date | None = Query(default=None, alias="from"),
    custom_end: date | None = Query(default=None, alias="to"),
    _: CurrentUser = Depends(get_current_user),
) -> AEDrillDownResponse:
    params, start, end = resolve_filter_params(
        manager=manager,
        ae_user_id=ae_id,
        ae_email=None,
        period=period,
        custom_start=custom_start,
        custom_end=custom_end,
    )
    sf = get_sf_client()
    try:
        result = fetch_ae_drilldown(sf, params, start, end, ae_id)
    except SalesforceAuthError as exc:
        log.error("Salesforce auth error: %s", exc)
        raise HTTPException(status_code=503, detail=f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        log.exception("AE drilldown fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Salesforce query failed: {exc}")
    if result is None:
        raise HTTPException(status_code=404, detail="AE not found")
    return result
