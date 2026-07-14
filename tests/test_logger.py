"""Tests for :mod:`insurance_kb.core.logger`."""

from __future__ import annotations

from pathlib import Path

import pytest

from insurance_kb.core.logger import configure_logging, get_logger


class TestLogger:
    """Verify the shared loguru logger is configured with console + file sinks."""

    @pytest.fixture(autouse=True)
    def _restore_default_logging(self):
        """Restore loguru's global sinks to the project's default ``logs/``
        directory after each test in this class.

        ``configure_logging(force=True)`` mutates loguru's process-wide
        singleton sinks. Without this teardown, a test that points sinks at
        a pytest ``tmp_path`` would leave that (soon-to-be-deleted) path
        wired in for the rest of the test session, silently affecting
        logging behavior in unrelated test modules that run afterward.
        """
        yield
        configure_logging(log_dir="logs", force=True)

    def test_get_logger_returns_bound_logger(self) -> None:
        logger = get_logger(__name__)
        # loguru's bound logger exposes standard level methods.
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_configure_logging_creates_log_directory(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "custom_logs"
        assert not log_dir.exists()
        configure_logging(log_dir=log_dir, force=True)
        assert log_dir.exists()

    def test_configure_logging_is_idempotent_without_force(self, tmp_path: Path) -> None:
        # First call (force=True) establishes a baseline configuration.
        configure_logging(log_dir=tmp_path / "logs_a", force=True)
        # Second call without force must be a no-op: logs_b is NOT created.
        configure_logging(log_dir=tmp_path / "logs_b")
        assert not (tmp_path / "logs_b").exists()

    def test_logging_does_not_raise(self) -> None:
        logger = get_logger(__name__)
        logger.info("Hello Pipeline test log line")
        logger.debug("debug level test log line")
        logger.warning("warning level test log line")
