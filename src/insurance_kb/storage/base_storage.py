"""Abstract interface abstracting where raw and processed files are
persisted (local filesystem today; object storage such as S3 in the
future — design doc section ⑧)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseStorage(ABC):
    """Interface every storage backend implementation must satisfy.

    Abstracting storage behind this interface allows the platform to
    start on local disk and later move to an object store (S3, Azure
    Blob) without changing any pipeline stage code — only the
    :class:`~insurance_kb.container.di_container.DIContainer` wiring
    needs to change.
    """

    @abstractmethod
    def save_bytes(self, key: str, data: bytes) -> str:
        """Persist raw bytes under a storage key.

        Args:
            key: Logical path/key to store the data under, e.g.
                ``"raw/samsung_fire/health/product_v1.pdf"``.
            data: The raw bytes to persist.

        Returns:
            The resolved location (e.g. absolute path or URI) the data was
            written to.

        Raises:
            insurance_kb.core.exceptions.StorageException: If the write fails.
        """
        raise NotImplementedError

    @abstractmethod
    def save_text(self, key: str, text: str) -> str:
        """Persist a text string under a storage key.

        Args:
            key: Logical path/key to store the text under.
            text: The text content to persist.

        Returns:
            The resolved location the text was written to.

        Raises:
            insurance_kb.core.exceptions.StorageException: If the write fails.
        """
        raise NotImplementedError

    @abstractmethod
    def load_bytes(self, key: str) -> bytes:
        """Read raw bytes previously stored under a key.

        Args:
            key: Logical path/key to read from.

        Returns:
            The raw bytes stored under ``key``.

        Raises:
            insurance_kb.core.exceptions.StorageException: If the key does
                not exist or cannot be read.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check whether data exists under a given storage key.

        Args:
            key: Logical path/key to check.

        Returns:
            ``True`` if data exists under ``key``, otherwise ``False``.
        """
        raise NotImplementedError
