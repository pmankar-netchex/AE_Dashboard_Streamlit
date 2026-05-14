from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


def render_and_send(
    *,
    recipients: list[str],
    subject: str,
    filters: dict,
) -> str:
    """Fetch dashboard → render All Source Summary → email it. Returns the
    SendGrid message id (or '' when SENDGRID_API_KEY isn't set).

    Pure: no schedule lookup, no run-history update — used by both scheduled
    jobs (which add their own bookkeeping) and the one-off send-now path.
    """
    from app.services.dashboard_service import fetch_dashboard, resolve_filter_params
    from app.services.email_service import get_email_service
    from app.services.report_renderer import render_all_source_summary
    from app.services.salesforce_client import get_sf_client

    if not recipients:
        raise ValueError("recipients is empty")

    f = filters or {}
    period = f.get("period") or "this_month"
    custom_start = _parse_date(f.get("from"))
    custom_end = _parse_date(f.get("to"))
    params, start, end = resolve_filter_params(
        manager=f.get("manager"),
        ae_user_id=f.get("ae_id"),
        ae_email=None,
        period=period,
        custom_start=custom_start,
        custom_end=custom_end,
    )

    sf = get_sf_client()
    response = fetch_dashboard(sf, params, start, end)
    html = render_all_source_summary(response, subject=subject)
    return get_email_service().send_html(to=recipients, subject=subject, html=html)


def run_scheduled_report(schedule_id: str) -> str:
    """Execute one scheduled report (cron-triggered or send-now on an existing
    schedule). Records a run row + audit on the schedule entity."""
    from app.services.audit_service import get_audit_service
    from app.services.schedule_service import get_schedule_service

    schedules = get_schedule_service()
    schedule = schedules.get(schedule_id)
    if schedule is None:
        logger.warning("scheduled job for missing schedule %s", schedule_id)
        return ""
    if not schedule.is_active:
        logger.info("schedule %s inactive — skipping", schedule_id)
        return ""

    try:
        msg_id = render_and_send(
            recipients=schedule.recipients,
            subject=schedule.subject,
            filters=schedule.filters or {},
        )
    except Exception as exc:
        schedules.record_run(schedule_id, ok=False, message=str(exc))
        get_audit_service().write(
            actor="scheduler",
            entity="schedule",
            action="run-failed",
            target=schedule_id,
            details={"error": str(exc)},
        )
        raise

    schedules.record_run(schedule_id, ok=True, message=msg_id)
    get_audit_service().write(
        actor="scheduler",
        entity="schedule",
        action="run",
        target=schedule_id,
        details={"message_id": msg_id, "recipients": len(schedule.recipients)},
    )
    return msg_id


def _parse_date(v) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v))
    except ValueError:
        return None
