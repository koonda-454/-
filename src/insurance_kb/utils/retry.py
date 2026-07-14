"""Retry decorator utilities, wrapping ``tenacity`` with project defaults.

Network- and I/O-bound operations (downloads, LLM API calls, future
crawler requests) should use :func:`with_retry` instead of hand-rolled
retry loops, so retry policy stays consistent and centrally tunable.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from insurance_kb.core.logger import get_logger
from insurance_kb.utils.constants import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_MAX_WAIT_SECONDS,
    DEFAULT_RETRY_MIN_WAIT_SECONDS,
)

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., object])


def with_retry(
    exceptions: tuple[type[Exception], ...] = (Exception,),
    attempts: int = DEFAULT_RETRY_ATTEMPTS,
    min_wait: float = DEFAULT_RETRY_MIN_WAIT_SECONDS,
    max_wait: float = DEFAULT_RETRY_MAX_WAIT_SECONDS,
) -> Callable[[F], F]:
    """Build a retry decorator with exponential backoff.

    Args:
        exceptions: Exception types that should trigger a retry.
        attempts: Maximum number of attempts before giving up.
        min_wait: Minimum wait time (seconds) between retries.
        max_wait: Maximum wait time (seconds) between retries.

    Returns:
        A decorator that applies retry-with-backoff to the wrapped function.

    Example:
        >>> @with_retry(exceptions=(ConnectionError,), attempts=3)
        ... def fetch() -> str:
        ...     ...
    """
    return retry(
        reraise=True,
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying after failure (attempt {retry_state.attempt_number}): "
            f"{retry_state.outcome.exception() if retry_state.outcome else 'unknown'}"
        ),
    )
