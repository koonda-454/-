"""Date/time parsing and formatting utilities.

Insurance company sites tend to publish dates in a handful of common
Korean formats (e.g. ``2026.05.10``, ``2026-05-10``, ``2026년 5월 10일``).
This module centralizes parsing so standardization logic doesn't need to
special-case each company's date format individually.
"""

from __future__ import annotations

import re
from datetime import datetime

_DATE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "%Y-%m-%d"),
    (re.compile(r"^\d{4}\.\d{2}\.\d{2}$"), "%Y.%m.%d"),
    (re.compile(r"^\d{4}/\d{2}/\d{2}$"), "%Y/%m/%d"),
)

_KOREAN_DATE_PATTERN = re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일")


def parse_flexible_date(raw_value: str) -> datetime | None:
    """Parse a date string in one of several common formats.

    Supported formats include ``YYYY-MM-DD``, ``YYYY.MM.DD``, ``YYYY/MM/DD``,
    and the Korean ``YYYY년 M월 D일`` style.

    Args:
        raw_value: The raw date string, as scraped from a source page.

    Returns:
        A parsed :class:`datetime`, or ``None`` if no known format matched.
    """
    value = raw_value.strip()

    korean_match = _KOREAN_DATE_PATTERN.search(value)
    if korean_match:
        year, month, day = (int(part) for part in korean_match.groups())
        return datetime(year=year, month=month, day=day)

    for pattern, fmt in _DATE_PATTERNS:
        if pattern.match(value):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                return None

    return None


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.utcnow().isoformat()


def to_date_string(value: datetime, fmt: str = "%Y%m%d") -> str:
    """Format a datetime as a compact date string, e.g. for filenames.

    Args:
        value: The datetime to format.
        fmt: strftime-style format string.

    Returns:
        The formatted date string.
    """
    return value.strftime(fmt)
