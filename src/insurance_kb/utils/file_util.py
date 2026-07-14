"""Filesystem helper utilities.

These helpers wrap common, repetitive filesystem operations (directory
creation, safe filename generation, JSON read/write) used across the
downloader, extraction, standardization, and storage modules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]+')


def ensure_dir(path: str | Path) -> Path:
    """Create a directory (and parents) if it doesn't already exist.

    Args:
        path: Directory path to ensure exists.

    Returns:
        The resolved :class:`Path` object for the directory.
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def safe_filename(name: str, replacement: str = "_") -> str:
    """Sanitize a string so it can be safely used as a filename.

    Args:
        name: The raw string (e.g. a product name) to sanitize.
        replacement: Character used to replace unsafe characters.

    Returns:
        A filesystem-safe filename fragment.
    """
    cleaned = _UNSAFE_FILENAME_CHARS.sub(replacement, name).strip()
    return cleaned or "unnamed"


def read_json(file_path: str | Path) -> Any:
    """Read and parse a JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        The parsed JSON content.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(file_path: str | Path, data: Any, indent: int = 2) -> Path:
    """Write data to a JSON file, creating parent directories as needed.

    Args:
        file_path: Destination path for the JSON file.
        data: JSON-serializable data to write.
        indent: Indentation level for pretty-printing.

    Returns:
        The resolved :class:`Path` the data was written to.
    """
    path = Path(file_path)
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, default=str)
    return path


def write_jsonl(file_path: str | Path, records: list[Any]) -> Path:
    """Write a list of records to a JSON Lines (``.jsonl``) file.

    Args:
        file_path: Destination path for the JSONL file.
        records: JSON-serializable records, one per line.

    Returns:
        The resolved :class:`Path` the data was written to.
    """
    path = Path(file_path)
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, default=str))
            f.write("\n")
    return path
