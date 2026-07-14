"""robots.txt fetching, parsing, and process-lifetime caching.

Per design doc constraints ("robots.txt 정책 준수") and the Phase 2 pilot
requirement to check robots.txt only once and cache the result, this
module fetches and parses a site's robots.txt the first time it's needed
and reuses the parsed result for every subsequent check within the same
process — avoiding a network round-trip before every single request.
"""

from __future__ import annotations

import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx

from insurance_kb.core.exceptions import CrawlerException
from insurance_kb.core.logger import get_logger

logger = get_logger(__name__)

# Process-lifetime cache: base URL (scheme + netloc) -> parsed RobotFileParser.
_ROBOTS_CACHE: dict[str, urllib.robotparser.RobotFileParser] = {}


def _base_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def get_robots_parser(
    url: str,
    timeout_seconds: float = 10.0,
    client: httpx.Client | None = None,
) -> urllib.robotparser.RobotFileParser:
    """Return a parsed ``robots.txt`` for the given URL's site, fetching and
    caching it on first use only.

    Args:
        url: Any URL on the target site; only its scheme+host is used to
            locate ``robots.txt``.
        timeout_seconds: HTTP timeout for the robots.txt fetch.
        client: Optional ``httpx.Client`` to use for the fetch (primarily
            for dependency injection in tests, e.g. with
            ``httpx.MockTransport``). Defaults to a one-off ``httpx.get``
            call when not provided.

    Returns:
        A populated :class:`urllib.robotparser.RobotFileParser`. If the
        fetch fails, a permissive-by-default parser with no rules is
        cached and returned so a transient robots.txt outage does not
        silently block all crawling forever, but the failure is logged
        loudly so a human can investigate.

    Raises:
        insurance_kb.core.exceptions.CrawlerException: If the robots.txt
            host cannot be resolved at all (e.g. malformed URL).
    """
    base = _base_url(url)
    if not base or "://" not in url:
        raise CrawlerException("Cannot determine robots.txt host from URL", context={"url": url})

    if base in _ROBOTS_CACHE:
        return _ROBOTS_CACHE[base]

    robots_url = urljoin(base, "/robots.txt")
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)

    try:
        if client is not None:
            response = client.get(robots_url, timeout=timeout_seconds, follow_redirects=True)
        else:
            response = httpx.get(robots_url, timeout=timeout_seconds, follow_redirects=True)
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
            logger.info(f"robots.txt fetched and cached: {robots_url}")
        else:
            # Per RFC 9309 convention: a missing robots.txt (404) means
            # "everything is allowed". Non-200/404 is treated the same way
            # here (permissive), but logged as a warning since it's unusual.
            parser.parse([])
            logger.warning(
                f"robots.txt returned HTTP {response.status_code}; "
                f"treating as permissive (no rules): {robots_url}"
            )
    except httpx.HTTPError as exc:
        parser.parse([])
        logger.error(f"Failed to fetch robots.txt, treating as permissive: {robots_url} ({exc})")

    _ROBOTS_CACHE[base] = parser
    return parser


def is_allowed(url: str, user_agent: str, client: httpx.Client | None = None) -> bool:
    """Check whether ``user_agent`` is allowed to fetch ``url`` per robots.txt.

    Uses the process-lifetime cache from :func:`get_robots_parser`, so the
    underlying robots.txt is only ever fetched once per site per process.

    Args:
        url: The URL to check.
        user_agent: The crawler's user agent string.
        client: Optional ``httpx.Client`` to use for the (at most once)
            robots.txt fetch. See :func:`get_robots_parser`.

    Returns:
        ``True`` if crawling ``url`` is permitted, ``False`` otherwise.
    """
    parser = get_robots_parser(url, client=client)
    return parser.can_fetch(user_agent, url)


def clear_cache() -> None:
    """Clear the process-lifetime robots.txt cache. Primarily used in tests."""
    _ROBOTS_CACHE.clear()
