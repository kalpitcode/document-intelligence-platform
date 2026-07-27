"""
Middleware Package
===================

Registers all middleware on the FastAPI application in the correct order.

**Architectural Rationale:**
- Middleware order matters — the first registered middleware is the
  outermost wrapper (executed first on request, last on response).
- Registers Security Headers, Rate Limiting, Request Size Limiting, Request ID,
  Processing Time, Logging, CORS, and GZip.
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.middlewares.logging import LoggingMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.request_id import RequestIDMiddleware
from app.middlewares.security import SecurityHeadersMiddleware
from app.middlewares.size_limit import RequestSizeLimitMiddleware
from app.middlewares.timing import ProcessingTimeMiddleware


def register_middleware(app: FastAPI) -> None:
    """Register all middleware on the FastAPI application."""
    settings = get_settings()

    # --- Logging (innermost custom middleware → runs closest to the handler) ---
    app.add_middleware(LoggingMiddleware)

    # --- Processing Time ---
    app.add_middleware(ProcessingTimeMiddleware)

    # --- Request Size Limiting (50MB cap) ---
    app.add_middleware(RequestSizeLimitMiddleware)

    # --- Rate Limiting (100 req/min default) ---
    app.add_middleware(RateLimitMiddleware)

    # --- Security Headers (HSTS, CSP, X-Frame-Options) ---
    app.add_middleware(SecurityHeadersMiddleware)

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
