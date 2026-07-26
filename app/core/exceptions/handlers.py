"""
Global Exception Handlers Module
==================================

Registers FastAPI exception handlers that translate application exceptions
into consistent JSON error responses.

**Architectural Rationale:**
- The API boundary is the ONLY place where exceptions are translated to HTTP.
- Services and repositories raise domain exceptions; they never import FastAPI.
- Every exception type maps to a specific HTTP status code and error schema.
- Unhandled exceptions return a generic 500 without leaking internal details.
- All errors are logged with full context for debugging.

**Connection to the system:**
- Registered on the FastAPI app instance in `app.main.create_application()`.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions.base import BaseAppException
from app.core.logging.context import get_request_id

logger = logging.getLogger(__name__)


def _build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    detail: dict[str, Any] | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> ORJSONResponse:
    """
    Build a standardized error response.

    Every error response follows this schema:
    {
        "success": false,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Human-readable message",
            "request_id": "uuid",
            "detail": {},
            "errors": []
        }
    }
    """
    body: dict[str, Any] = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "request_id": get_request_id(),
        },
    }
    if detail:
        body["error"]["detail"] = detail
    if errors:
        body["error"]["errors"] = errors

    return ORJSONResponse(status_code=status_code, content=body)


async def base_app_exception_handler(
    request: Request,
    exc: BaseAppException,
) -> ORJSONResponse:
    """
    Handle all application-defined exceptions.

    Maps `BaseAppException` (and subclasses) to structured JSON responses.
    """
    logger.error(
        "Application error: %s",
        exc.message,
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url),
            "method": request.method,
        },
        exc_info=exc,
    )

    errors = getattr(exc, "errors", None)
    return _build_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
        errors=errors,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> ORJSONResponse:
    """
    Handle Pydantic/FastAPI request validation errors.

    Translates FastAPI's validation errors into our standard error format.
    """
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(
        "Request validation failed",
        extra={
            "path": str(request.url),
            "method": request.method,
            "errors": errors,
        },
    )

    return _build_error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        errors=errors,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> ORJSONResponse:
    """
    Handle Starlette/FastAPI HTTP exceptions (404, 405, etc.).
    """
    logger.warning(
        "HTTP error: %s",
        exc.detail,
        extra={
            "status_code": exc.status_code,
            "path": str(request.url),
            "method": request.method,
        },
    )

    detail_message: str = (
        exc.detail if isinstance(exc.detail, str) else "HTTP error"
    )

    return _build_error_response(
        status_code=exc.status_code,
        error_code="HTTP_ERROR",
        message=detail_message,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> ORJSONResponse:
    """
    Catch-all handler for any unhandled exceptions.

    NEVER leaks internal error details to the client.
    Logs the full traceback for server-side debugging.
    """
    logger.critical(
        "Unhandled exception",
        extra={
            "path": str(request.url),
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
        exc_info=exc,
    )

    return _build_error_response(
        status_code=500,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application.

    Called during application factory setup.

    Args:
        app: The FastAPI application instance.
    """
    app.add_exception_handler(BaseAppException, base_app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]
