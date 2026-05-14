from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_exception_handlers
from app.logging_setup import configure_logging
from app.routers import (
    audit,
    columns,
    dashboard,
    filters,
    health,
    me,
    salesforce,
    schedules,
    soql,
    users,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    from app.config import get_settings
    from app.scheduler import start_scheduler, stop_scheduler
    from app.schedulers_registration import sync_all_schedules
    from app.storage.migrations import bootstrap_admins, ensure_tables

    ensure_tables()
    bootstrap_admins(get_settings().bootstrap_admin_list)
    start_scheduler()
    sync_all_schedules()
    try:
        yield
    finally:
        stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AE Dashboard API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.ui_origin] if settings.env == "dev" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(me.router)
    app.include_router(salesforce.router)
    app.include_router(columns.router)
    app.include_router(filters.router)
    app.include_router(dashboard.router)
    app.include_router(soql.router)
    app.include_router(users.router)
    app.include_router(audit.router)
    app.include_router(schedules.router)

    return app


app = create_app()
