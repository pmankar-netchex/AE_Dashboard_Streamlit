from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_exception_handlers
from app.logging_setup import configure_logging
from app.routers import health, me, salesforce


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Provision storage + seed bootstrap admins (no-op when storage unconfigured)
    from app.config import get_settings
    from app.storage.migrations import bootstrap_admins, ensure_tables

    ensure_tables()
    bootstrap_admins(get_settings().bootstrap_admin_list)
    yield


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

    return app


app = create_app()
