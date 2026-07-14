"""Local filesystem implementation of :class:`BaseStorage`.

This is the default storage backend for Phase 1. It performs plain file
I/O only — no PDF processing, no network access — and exists so the
:class:`~insurance_kb.container.di_container.DIContainer` and Hello
Pipeline have a concrete, working ``Storage`` to wire in, demonstrating
that the storage backend can be swapped later (e.g. for an S3-backed
implementation) without touching any pipeline stage code.
"""

from __future__ import annotations

from pathlib import Path

from insurance_kb.core.exceptions import StorageException
from insurance_kb.core.logger import get_logger
from insurance_kb.storage.base_storage import BaseStorage

logger = get_logger(__name__)


class LocalFileStorage(BaseStorage):
    """Stores data as files under a configurable root directory.

    Args:
        root_dir: Base directory all storage keys are resolved relative to.
    """

    def __init__(self, root_dir: str | Path = "data") -> None:
        self._root_dir = Path(root_dir)

    def _resolve(self, key: str) -> Path:
        return self._root_dir / key

    def save_bytes(self, key: str, data: bytes) -> str:
        """See :meth:`BaseStorage.save_bytes`."""
        path = self._resolve(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except OSError as exc:
            raise StorageException(
                "Failed to write bytes to storage", context={"key": key, "error": str(exc)}
            ) from exc
        logger.debug(f"Saved bytes to storage: {path}")
        return str(path)

    def save_text(self, key: str, text: str) -> str:
        """See :meth:`BaseStorage.save_text`."""
        path = self._resolve(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise StorageException(
                "Failed to write text to storage", context={"key": key, "error": str(exc)}
            ) from exc
        logger.debug(f"Saved text to storage: {path}")
        return str(path)

    def load_bytes(self, key: str) -> bytes:
        """See :meth:`BaseStorage.load_bytes`."""
        path = self._resolve(key)
        if not path.exists():
            raise StorageException("Storage key not found", context={"key": key})
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageException(
                "Failed to read bytes from storage", context={"key": key, "error": str(exc)}
            ) from exc

    def exists(self, key: str) -> bool:
        """See :meth:`BaseStorage.exists`."""
        return self._resolve(key).exists()
