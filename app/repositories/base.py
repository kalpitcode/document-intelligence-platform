"""
Base Repository Module
=======================

Generic repository implementation for database CRUD operations.

**Architectural Rationale:**
- Abstracts raw database queries away from services and controllers.
- Enforces strict typing with Generic Model `T`.
- Automatically handles soft deletion when entities support `SoftDeleteMixin`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing core CRUD operations for SQLAlchemy models.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """
        Initialize repository with model class and session instance.

        Args:
            model: SQLAlchemy model class.
            session: Active AsyncSession instance.
        """
        self.model = model
        self.session = session

    async def get_by_id(self, id: uuid.UUID | str) -> ModelType | None:
        """
        Retrieve a single entity by its primary key UUID.

        Args:
            id: Entity UUID.

        Returns:
            Model instance if found, None otherwise.
        """
        if isinstance(id, str):
            id = uuid.UUID(id)

        stmt = select(self.model).where(getattr(self.model, "id") == id)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelType]:
        """
        Retrieve multiple entities with pagination offsets.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            Sequence of model instances.
        """
        stmt = select(self.model)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs: object) -> ModelType:
        """
        Create and persist a new model instance.

        Args:
            **kwargs: Column name-value pairs.

        Returns:
            Persisted model instance.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelType, **kwargs: object) -> ModelType:
        """
        Update attributes of an existing model instance.

        Args:
            instance: Model instance to update.
            **kwargs: Attributes to modify.

        Returns:
            Updated model instance.
        """
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType, soft: bool = True) -> None:
        """
        Delete a model instance (soft delete if supported, otherwise hard delete).

        Args:
            instance: Model instance to remove.
            soft: If True and model supports SoftDeleteMixin, set is_deleted=True.
        """
        if soft and hasattr(instance, "soft_delete"):
            instance.soft_delete()
            self.session.add(instance)
        else:
            await self.session.delete(instance)

        await self.session.flush()
