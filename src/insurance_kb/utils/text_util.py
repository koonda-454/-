"""Text normalization and lightweight chunking helpers.

These helpers support the standardization layer (normalizing extracted
text before mapping to canonical fields) and the chunking layer (splitting
long text into retrieval-sized pieces). They intentionally avoid any
insurance-domain-specific logic; that belongs in the standardization
modules that consume these helpers.
"""

from __future__ import annotations

import re

_WHITESPACE_PATTERN = re.compile(r"[ \t\u3000]+")
_MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace and blank lines in extracted text.

    Args:
        text: Raw extracted text, potentially containing PDF extraction
            artifacts such as repeated spaces or excessive blank lines.

    Returns:
        Text with normalized whitespace.
    """
    collapsed = _WHITESPACE_PATTERN.sub(" ", text)
    collapsed = _MULTI_NEWLINE_PATTERN.sub("\n\n", collapsed)
    return collapsed.strip()


def split_into_chunks(
    text: str, max_chars: int = 800, overlap_chars: int = 100
) -> list[str]:
    """Split text into overlapping chunks of roughly ``max_chars`` length.

    This is a simple, dependency-free character-based splitter suitable
    for Phase 1 scaffolding. It prefers to break on paragraph or sentence
    boundaries when possible to avoid cutting sentences mid-word.

    Args:
        text: The text to split.
        max_chars: Approximate maximum characters per chunk.
        overlap_chars: Number of characters to overlap between consecutive
            chunks, to preserve context across chunk boundaries.

    Returns:
        A list of text chunks. Returns an empty list for empty input.
    """
    normalized = normalize_whitespace(text)
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(start + max_chars, text_length)
        chunk = normalized[start:end]
        chunks.append(chunk.strip())
        if end >= text_length:
            break
        start = end - overlap_chars if end - overlap_chars > start else end

    return [c for c in chunks if c]


def truncate(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to a maximum length, appending a suffix if truncated.

    Args:
        text: The text to truncate.
        max_length: Maximum length before truncation.
        suffix: Suffix appended when truncation occurs.

    Returns:
        The original text if within length, otherwise a truncated version.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)].rstrip() + suffix
