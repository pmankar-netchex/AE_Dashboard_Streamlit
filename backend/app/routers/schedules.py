from __future__ import annotations

import logging

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user, require_admin
from app.schedulers_registration import register_schedule, unregister_schedule
from app.schemas.common import CurrentUser
from app.schemas.schedules import (
    ScheduleCreateIn,
    ScheduleOut,
    ScheduleUpdateIn,
    SendNowResult,
)
from app.services.audit_service import get_audit_service
from app.services.schedule_service import get_schedule_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleOut])
def list_schedules(
    _: CurrentUser = Depends(get_current_user),
) -> list[ScheduleOut]:
    return get_schedule_service().list()


@router.post("", response_model=ScheduleOut, status_code=201)
def create_schedule(
    body: ScheduleCreateIn, actor: CurrentUser = Depends(require_admin)
) -> ScheduleOut:
    try:
        CronTrigger.from_crontab(body.cron)
    except Exception as exc:
        raise HTTPException(400, detail=f"invalid cron: {exc}")
    schedule = get_schedule_service().create(
        name=body.name,
        cron=body.cron,
        recipients=body.recipients,
        subject=body.subject,
        filters=body.filters,
        is_active=body.is_active,
        actor=actor.email,
    )
    register_schedule(schedule)
    get_audit_service().write(
        actor=actor.email,
        entity="schedule",
        action="create",
        target=schedule.id,
        details={"name": schedule.name, "cron": schedule.cron},
    )
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: str,
    body: ScheduleUpdateIn,
    actor: CurrentUser = Depends(require_admin),
) -> ScheduleOut:
    if body.cron is not None:
        try:
            CronTrigger.from_crontab(body.cron)
        except Exception as exc:
            raise HTTPException(400, detail=f"invalid cron: {exc}")
    updated = get_schedule_service().update(schedule_id, **body.model_dump())
    if updated is None:
        raise HTTPException(404, detail="schedule not found")
    register_schedule(updated)
    get_audit_service().write(
        actor=actor.email,
        entity="schedule",
        action="update",
        target=schedule_id,
    )
    return updated


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: str, actor: CurrentUser = Depends(require_admin)
) -> None:
    svc = get_schedule_service()
    if not svc.delete(schedule_id):
        raise HTTPException(404, detail="schedule not found")
    unregister_schedule(schedule_id)
    get_audit_service().write(
        actor=actor.email,
        entity="schedule",
        action="delete",
        target=schedule_id,
    )
    return None


@router.post("/{schedule_id}/send-now", response_model=SendNowResult)
def send_now(
    schedule_id: str, actor: CurrentUser = Depends(require_admin)
) -> SendNowResult:
    svc = get_schedule_service()
    schedule = svc.get(schedule_id)
    if schedule is None:
        raise HTTPException(404, detail="schedule not found")
    # Run synchronously so the caller gets feedback. The scheduled invocation
    # uses the same function via APScheduler.
    from app.scheduler.jobs import run_scheduled_report

    try:
        msg_id = run_scheduled_report(schedule_id)
        get_audit_service().write(
            actor=actor.email,
            entity="schedule",
            action="send-now",
            target=schedule_id,
            details={"message_id": msg_id},
        )
        return SendNowResult(ok=True, message_id=msg_id or "")
    except Exception as exc:
        get_audit_service().write(
            actor=actor.email,
            entity="schedule",
            action="send-now-failed",
            target=schedule_id,
            details={"error": str(exc)},
        )
        return SendNowResult(ok=False, error=str(exc))
