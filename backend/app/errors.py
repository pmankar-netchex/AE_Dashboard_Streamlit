from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.salesforce_client import (
    SalesforceAuthError,
    SalesforceSessionError,
    get_token_cache,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "code": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exc(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "validation_error", "code": 422, "detail": exc.errors()},
        )

    @app.exception_handler(SalesforceAuthError)
    async def sf_auth_exc(request: Request, exc: SalesforceAuthError) -> JSONResponse:
        status = get_token_cache().status()
        error_code = (
            "sf_session_expired"
            if isinstance(exc, SalesforceSessionError)
            else "sf_auth_failed"
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": str(exc),
                "code": 503,
                "error_code": error_code,
                "instance_url": status.instance_url,
                "last_success_at": status.last_success_at,
            },
        )
