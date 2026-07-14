"""Custom exception hierarchy for the Insurance AI Knowledge Platform.

All exceptions raised by pipeline stages should inherit from
:class:`InsuranceKBException` so that callers can catch the entire
platform's exceptions with a single ``except InsuranceKBException`` clause,
while still being able to catch narrower, stage-specific exceptions when
finer-grained handling is required.
"""

from __future__ import annotations

from typing import Any


class InsuranceKBException(Exception):
    """Base exception for every error raised within this platform.

    Args:
        message: Human-readable description of the error.
        context: Optional structured context (e.g. product_id, company)
            useful for logging and debugging.
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        self.message = message
        self.context = context or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if not self.context:
            return self.message
        context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{self.message} ({context_str})"


class ConfigException(InsuranceKBException):
    """Raised when configuration loading or validation fails."""


class CrawlerException(InsuranceKBException):
    """Raised when a crawler (Collector) fails to collect product listings."""


class DownloadException(InsuranceKBException):
    """Raised when a file download (e.g. PDF) fails."""


class ExtractionException(InsuranceKBException):
    """Raised when text/OCR extraction from a source document fails."""


class StandardizationException(InsuranceKBException):
    """Raised when mapping raw structured data to the canonical schema fails."""


class ValidationException(InsuranceKBException):
    """Raised when a domain model fails validation beyond what Pydantic checks."""


class KnowledgeBuilderException(InsuranceKBException):
    """Raised when an AI Knowledge Builder generator fails to produce output."""


class ExportException(InsuranceKBException):
    """Raised when exporting knowledge artifacts to an external target fails."""


class StorageException(InsuranceKBException):
    """Raised when a storage backend read/write operation fails."""


class RepositoryException(InsuranceKBException):
    """Raised when a repository operation (persistence layer) fails."""


class PipelineException(InsuranceKBException):
    """Raised when the pipeline orchestration itself fails."""
