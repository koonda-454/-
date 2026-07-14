"""Generic Repository Pattern interface over domain models.

Repositories decouple pipeline/orchestration code from *how* domain
objects are persisted (in-memory for Phase 1, SQLite/PostgreSQL via
SQLAlchemy in later phases). Every concrete repository implements this
same interface regardless of backend, so swapping the backend never
requires touching calling code (design doc section ⑥ DI, and the
Clean Architecture / Repository Pattern requirement for this phase).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TModel = TypeVar("TModel")


class BaseRepository(ABC, Generic[TModel]):
    """Generic CRUD-style repository interface for a domain model type.

    Type Parameters:
        TModel: The domain model type this repository manages
            (e.g. :class:`~insurance_kb.models.product.Product`).
    """

    @abstractmethod
    def add(self, entity: TModel) -> TModel:
        """Persist a new entity.

        Args:
            entity: The domain model instance to persist.

        Returns:
            The persisted entity (potentially with server-assigned fields).

        Raises:
            insurance_kb.core.exceptions.RepositoryException: If persistence fails.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, entity_id: str) -> TModel | None:
        """Retrieve a single entity by its identifier.

        Args:
            entity_id: The identifier of the entity to retrieve.

        Returns:
            The matching entity, or ``None`` if not found.
        """
        raise NotImplementedError

    @abstractmethod
    def list(self) -> list[TModel]:
        """Retrieve all entities currently managed by this repository.

        Returns:
            A list of all stored entities.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity by its identifier.

        Args:
            entity_id: The identifier of the entity to delete.

        Returns:
            ``True`` if an entity was deleted, ``False`` if none matched.
        """
        raise NotImplementedError
