"""Hashing utilities used for change detection (design doc section 7)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from insurance_kb.utils.constants import DEFAULT_HASH_ALGORITHM, DEFAULT_HASH_CHUNK_SIZE_BYTES


def compute_file_hash(
    file_path: str | Path,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = DEFAULT_HASH_CHUNK_SIZE_BYTES,
) -> str:
    """Compute a hex digest hash of a file's contents, streamed in chunks.

    Args:
        file_path: Path to the file to hash.
        algorithm: Name of the hashlib algorithm to use (default: sha256).
        chunk_size: Number of bytes to read per iteration.

    Returns:
        The hex digest string of the file's contents.

    Raises:
        FileNotFoundError: If ``file_path`` does not exist.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Cannot hash missing file: {path}")

    hasher = hashlib.new(algorithm)
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_text_hash(text: str, algorithm: str = DEFAULT_HASH_ALGORITHM) -> str:
    """Compute a hex digest hash of a text string.

    Args:
        text: The text content to hash.
        algorithm: Name of the hashlib algorithm to use (default: sha256).

    Returns:
        The hex digest string of the UTF-8 encoded text.
    """
    hasher = hashlib.new(algorithm)
    hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()


def compute_bytes_hash(data: bytes, algorithm: str = DEFAULT_HASH_ALGORITHM) -> str:
    """Compute a hex digest hash of raw bytes (e.g. an in-memory downloaded file).

    Added for Phase 2 (Samsung Fire pilot): downloaders receive PDF bytes
    directly from an HTTP response and need a standard SHA-256 of the
    exact bytes, without writing to disk first (unlike
    :func:`compute_file_hash`) and without the encoding ambiguity of
    :func:`compute_text_hash` (which is for text, not arbitrary binary data).

    Args:
        data: Raw bytes to hash.
        algorithm: Name of the hashlib algorithm to use (default: sha256).

    Returns:
        The hex digest string of the bytes.
    """
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def hashes_match(hash_a: str, hash_b: str) -> bool:
    """Case-insensitively compare two hex digest hashes.

    Args:
        hash_a: First hash to compare.
        hash_b: Second hash to compare.

    Returns:
        ``True`` if the two hashes represent the same digest.
    """
    return hash_a.strip().lower() == hash_b.strip().lower()
