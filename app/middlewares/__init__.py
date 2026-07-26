"""
Middleware Package
===================

Registers all middleware on the FastAPI application in the correct order.

**Architectural Rationale:**
- Middleware order matters — the first registered middleware is the
  outermost wrapper (executed first on request, last on response).
- This module centralizes registration so the order is explicit and
  reviewable in one place.
- CORS, Trusted Hosts, and GZip are Starlette built-ins.
- Custom middleware (Request ID, Logging, Timing) implement our
  cross-cutting concerns.

**Middleware Execution Order (request flow):**
1. Trusted Hosts → reject requests from untrusted hosts
2. CORS → add CORS headers
3. GZip → compress responses
4. Request ID → assign unique ID
5. Processing Time → start timer
6. Logging → log request details
7. Route Handler → business logic

**Connection to the system:**
- Called once by `app.main.create_application()` during startup.
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.middlewares.logging import LoggingMiddleware
from app.middlewares.request_id import RequestIDMiddleware
from app.middlewares.timing import ProcessingTimeMiddleware


def register_middleware(app: FastAPI) -> None:
    """
    Register all middleware on the FastAPI application.

    Middleware is registered in reverse execution order — the last
    registered middleware is the outermost wrapper (executed first).

    Args:
        app: The FastAPI application instance.
    """
    settings = get_settings()

    # --- Logging (innermost custom middleware → runs closest to the handler) ---
    app.add_middleware(LoggingMiddleware)

    # --- Processing Time ---
    app.add_middleware(ProcessingTimeMiddleware)

    # --- Request ID (must be before logging so request_id is available) ---
    app.add_middleware(RequestIDMiddleware)

    # --- GZip Compression ---
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # --- Trusted Hosts (outermost — rejects untrusted hosts immediately) ---
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.trusted_hosts,
        )
