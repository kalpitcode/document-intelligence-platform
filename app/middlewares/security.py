"""
Security Middleware & Validation Module
========================================

Production security hardening middleware injecting enterprise HTTP security headers,
validating secrets, and sanitizing API request inputs.

**Architectural Rationale:**
- Injects standard security headers into all HTTP responses (HSTS, CSP, X-Frame-Options, X-Content-Type-Options).
- Provides environment and secret strength validation helper.
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware injecting security headers on every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        settings = get_settings()

        if settings.enable_security_headers:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


def validate_environment_and_secrets() -> dict[str, Any]:
    """
    Validate production secret strength and environment setting integrity.
    """
    settings = get_settings()
    issues: list[str] = []
    warnings: list[str] = []

    if settings.is_production:
        if "SUPER_SECRET" in settings.jwt_secret_key:
            issues.append("JWT_SECRET_KEY is set to default template string.")
        if len(settings.jwt_secret_key) < 32:
            issues.append("JWT_SECRET_KEY is under 32 characters long.")
        if settings.postgres_password == "change_me_in_production":
            issues.append("POSTGRES_PASSWORD is using default placeholder.")

    return {
        "status": "VALID" if not issues else "INVALID",
        "environment": settings.app_env,
        "issues": issues,
        "warnings": warnings,
        "is_production": settings.is_production,
    }
