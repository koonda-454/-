"""In-memory implementation of the Product repository.

This is a Phase 1 placeholder implementation used to validate the
Repository Pattern interface end-to-end (via the Hello Pipeline and unit
tests) without standing up a real database. It should be swapped for a
SQLAlchemy-backed repository in a later phase without any change to
callers, since both conform to :class:`BaseRepository`.
"""

from __future__ import annotations

from insurance_kb.core.exceptions import RepositoryException
from insurance_kb.core.logger import get_logger
from insurance_kb.models.product import Product
from insurance_kb.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class InMemoryProductRepository(BaseRepository[Product]):
    """A simple dict-backed, process-local repository for :class:`Product`."""

    def __init__(self) -> None:
        self._store: dict[str, Product] = {}

    def add(self, entity: Product) -> Product:
        """Store a product, keyed by its ``product_id``.

        Args:
            entity: The product to store.

        Returns:
            The stored product.

        Raises:
            insurance_kb.core.exceptions.RepositoryException: If a product
                with the same ID already exists.
        """
        if entity.product_id in self._store:
            raise RepositoryException(
                "Product already exists", context={"product_id": entity.product_id}
            )
        self._store[entity.product_id] = entity
        logger.debug(f"Added product to repository: {entity.product_id}")
        return entity

    def get(self, entity_id: str) -> Product | None:
        """Retrieve a product by its ``product_id``."""
        return self._store.get(entity_id)

    def list(self) -> list[Product]:
        """Return all products currently stored."""
        return list(self._store.values())

    def delete(self, entity_id: str) -> bool:
        """Delete a product by its ``product_id``."""
        if entity_id in self._store:
            del self._store[entity_id]
            return True
        return False
