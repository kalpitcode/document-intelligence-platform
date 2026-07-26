"""
RabbitMQ Connection Manager
=============================

Manages the async RabbitMQ connection lifecycle using aio-pika.

**Architectural Rationale:**
- Encapsulates all RabbitMQ concerns in a single manager class (SRP).
- Uses `aio_pika` for AMQP 0-9-1 protocol with async/await support.
- Connection is robust (auto-reconnect) for production reliability.
- Health check verifies connectivity for the `/health` endpoint.
- Channels are acquired per-operation to avoid channel leaks.

**Connection to the system:**
- `init()` / `close()` called by app startup/shutdown events in `app.main`.
- `get_channel()` provides a channel for publishing/consuming messages.
- `health_check()` called by the health endpoint.
"""

from __future__ import annotations

import logging
from typing import Any

import aio_pika
from aio_pika import Channel
from aio_pika.abc import AbstractRobustConnection

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RabbitMQManager:
    """
    Manages the RabbitMQ connection and channel lifecycle.

    Usage::

        rabbitmq_manager = RabbitMQManager()
        await rabbitmq_manager.init()

        async with rabbitmq_manager.get_channel() as channel:
            await channel.default_exchange.publish(
                aio_pika.Message(body=b"hello"),
                routing_key="my_queue",
            )

        await rabbitmq_manager.close()
    """

    def __init__(self) -> None:
        self._connection: AbstractRobustConnection | None = None

    async def init(self) -> None:
        """
        Initialize the RabbitMQ connection.

        Uses robust connection for automatic reconnection on failures.
        """
        settings = get_settings()

        try:
            self._connection = await aio_pika.connect_robust(
                url=settings.rabbitmq_url,
                timeout=10.0,
                client_properties={
                    "connection_name": settings.app_name,
                },
            )

            logger.info(
                "RabbitMQ connection established",
                extra={
                    "host": settings.rabbitmq_host,
                    "port": settings.rabbitmq_port,
                    "vhost": settings.rabbitmq_vhost,
                },
            )
        except Exception as exc:
            logger.error(
                "Failed to connect to RabbitMQ",
                exc_info=exc,
                extra={
                    "host": settings.rabbitmq_host,
                    "port": settings.rabbitmq_port,
                },
            )
            # Don't raise — let the app start without RabbitMQ.
            # Health endpoint will report unhealthy status.
            self._connection = None

    async def close(self) -> None:
        """Close the RabbitMQ connection."""
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQ connection closed")

        self._connection = None

    async def get_channel(self) -> Channel:
        """
        Acquire a new channel from the connection.

        Returns:
            An aio_pika Channel instance.

        Raises:
            RuntimeError: If the connection is not established.
        """
        if self._connection is None or self._connection.is_closed:
            msg = "RabbitMQ not connected. Call init() first."
            raise RuntimeError(msg)

        channel = await self._connection.channel()
        return channel  # type: ignore[return-value]

    async def health_check(self) -> dict[str, Any]:
        """
        Verify RabbitMQ connectivity.

        Returns:
            Dictionary with connection status.
        """
        if self._connection is None:
            return {"status": "unhealthy", "error": "Connection not initialized"}

        try:
            if self._connection.is_closed:
                return {"status": "unhealthy", "error": "Connection is closed"}

            # Attempt to open and close a channel as a connectivity test
            channel = await self._connection.channel()
            await channel.close()
            return {"status": "healthy"}
        except Exception as exc:
            logger.error("RabbitMQ health check failed", exc_info=exc)
            return {"status": "unhealthy", "error": str(exc)}


# Module-level singleton instance
rabbitmq_manager = RabbitMQManager()
