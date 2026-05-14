from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user
from app.legacy.time_filters import PRESETS
from app.schemas.common import CurrentUser
from app.schemas.filters import AEOption, ManagerOption, TimePresetOption
from app.services.filter_service import get_filter_service
from app.services.salesforce_client import get_sf_client

router = APIRouter(prefix="/api/filters", tags=["filters"])


@router.get("/managers", response_model=list[ManagerOption])
def list_managers(_: CurrentUser = Depends(get_current_user)) -> list[ManagerOption]:
    sf = get_sf_client()
    names = get_filter_service().managers(sf)
    return [ManagerOption(name=n) for n in names]


@router.get("/aes", response_model=list[AEOption])
def list_aes(
    manager: str | None = Query(default=None),
    _: CurrentUser = Depends(get_current_user),
) -> list[AEOption]:
    sf = get_sf_client()
    rows = get_filter_service().aes(sf, manager=manager)
    return [
        AEOption(
            id=r["id"],
            name=r["name"],
            email=r.get("email", ""),
            manager=manager,
        )
        for r in rows
    ]


_PRESET_LABELS = {
    "this_week": "This Week",
    "last_week": "Last Week",
    "this_month": "This Month",
    "last_month": "Last Month",
}


@router.get("/time-presets", response_model=list[TimePresetOption])
def list_time_presets(_: CurrentUser = Depends(get_current_user)) -> list[TimePresetOption]:
    return [
        TimePresetOption(key=k, display_name=_PRESET_LABELS[k])
        for k in PRESETS.keys()
    ] + [TimePresetOption(key="custom", display_name="Custom")]
