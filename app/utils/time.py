"""
Time Utility Module
====================

Provides timezone-aware datetime helpers.

**Architectural Rationale:**
- All timestamps in the application are UTC to avoid timezone ambiguity.
- ISO 8601 is the standard format for API responses and log entries.
- Centralized time functions prevent inconsistent timezone handling
  across the codebase.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    """Get the current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


def utc_now_iso() -> str:
    """Get the current UTC datetime as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def to_iso(dt: datetime) -> str:
    """
    Convert a datetime to ISO 8601 string.

    Args:
        dt: Datetime to convert.

    Returns:
        ISO 8601 formatted string.
    """
    return dt.isoformat()


def from_iso(iso_string: str) -> datetime:
    """
    Parse an ISO 8601 string into a datetime.

    Args:
        iso_string: ISO 8601 formatted string.

    Returns:
        Parsed datetime object.
    """
    return datetime.fromisoformat(iso_string)


def unix_timestamp() -> float:
    """Get the current UTC time as a Unix timestamp (seconds since epoch)."""
    return datetime.now(UTC).timestamp()


def from_unix_timestamp(ts: float) -> datetime:
    """
    Convert a Unix timestamp to a UTC datetime.

    Args:
        ts: Unix timestamp (seconds since epoch).

    Returns:
        UTC datetime.
    """
    return datetime.fromtimestamp(ts, tz=UTC)


def time_ago(seconds: int) -> datetime:
    """
    Get a UTC datetime that is `seconds` ago from now.

    Args:
        seconds: Number of seconds in the past.

    Returns:
        UTC datetime.
    """
    return datetime.now(UTC) - timedelta(seconds=seconds)


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds into a human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Human-readable duration (e.g., "2h 30m 15s").
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"

    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)
