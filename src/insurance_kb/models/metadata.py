"""Domain model representing a single pipeline execution's metadata/log
record, corresponding to the ``crawl_logs`` metadata table (design doc
section 10)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Overall status of a single pipeline run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class Metadata(BaseModel):
    """Summary metadata for a single pipeline execution run.

    Attributes:
        run_id: Stable identifier for this pipeline run.
        company_id: Company this run targeted, if scoped to one company.
        run_at: Timestamp the run started.
        status: Overall outcome of the run.
        new_count: Number of newly discovered products/versions.
        updated_count: Number of products/versions that changed.
        error_count: Number of errors encountered during the run.
        error_detail: Free-form details for failures, if any.
    """

    run_id: str = Field(..., description="Stable identifier for this pipeline run.")
    company_id: str | None = Field(default=None, description="Company this run targeted.")
    run_at: datetime = Field(default_factory=datetime.utcnow)
    status: RunStatus = Field(default=RunStatus.SUCCESS)
    new_count: int = Field(default=0, ge=0)
    updated_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    error_detail: str | None = Field(default=None, description="Free-form failure details.")
