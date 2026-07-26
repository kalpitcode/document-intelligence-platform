"""
Messaging Package
==================

RabbitMQ connection management for the Document Intelligence Platform.

Usage::

    from app.core.messaging import rabbitmq_manager

    await rabbitmq_manager.init()
    channel = await rabbitmq_manager.get_channel()
"""

from __future__ import annotations

from app.core.messaging.rabbitmq import RabbitMQManager, rabbitmq_manager

__all__ = [
    "RabbitMQManager",
    "rabbitmq_manager",
]
