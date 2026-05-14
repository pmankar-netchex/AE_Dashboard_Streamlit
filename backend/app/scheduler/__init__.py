"""Process-wide BackgroundScheduler.

We deliberately use the in-memory APScheduler jobstore: schedules persist in
the `schedules` Azure Table (managed by schedule_service); on startup we
re-register every active row with APScheduler via sync_all_schedules. A
restart loses no state because the source of truth is our own table.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None
_lock = threading.Lock()


def build_scheduler() -> BackgroundScheduler:
    settings = get_settings()
    return BackgroundScheduler(
        jobstores={"default": MemoryJobStore()},
        timezone=settings.scheduler_tz,
    )


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    with _lock:
        if _scheduler is None:
            _scheduler = build_scheduler()
            _scheduler.start()
            logger.info("scheduler started (tz=%s)", get_settings().scheduler_tz)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    with _lock:
        if _scheduler is not None:
            try:
                _scheduler.shutdown(wait=False)
            except Exception:
                logger.exception("scheduler shutdown failed")
            _scheduler = None


def get_scheduler() -> BackgroundScheduler:
    if _scheduler is None:
        return start_scheduler()
    return _scheduler


def reset_scheduler() -> None:
    stop_scheduler()
