"""
Repositories Package
=====================

Data access layer implementing the Repository Pattern.

No repositories are defined yet — this package provides the
registration point for future repository modules.

All repositories should:
- Accept an `AsyncSession` via dependency injection.
- Contain ONLY data access logic (no business rules).
- Return domain entities or raise domain exceptions.
"""

from __future__ import annotations
