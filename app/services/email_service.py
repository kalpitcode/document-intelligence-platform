"""
Email Service Module (Mock)
============================

Mock email delivery service for email verification and password resets.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Mock service providing transactional email delivery logs."""

    @staticmethod
    async def send_verification_email(email: str, token: str) -> None:
        """Mock sending email verification link."""
        logger.info(
            "MOCK EMAIL: Sending verification link to %s (Token: %s)",
            email,
            token,
        )

    @staticmethod
    async def send_password_reset_email(email: str, token: str) -> None:
        """Mock sending password reset link."""
        logger.info(
            "MOCK EMAIL: Sending password reset link to %s (Token: %s)",
            email,
            token,
        )
