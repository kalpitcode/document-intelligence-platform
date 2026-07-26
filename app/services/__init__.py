"""
Services Package
==================

Business logic layer implementing the Service Pattern.

No services are defined yet — this package provides the
registration point for future service modules.

All services should:
- Contain business logic and orchestration.
- Use repositories for data access (never access DB directly).
- Be framework-agnostic (no FastAPI imports).
- Be independently testable.
"""

from __future__ import annotations
