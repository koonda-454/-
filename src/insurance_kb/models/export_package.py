"""Domain model representing a bundle of chunks/artifacts prepared for
export to an external consumer (ChatGPT Project, RAG platform, etc.),
per design doc section 12."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from insurance_kb.models.chunk import Chunk


class ExportTarget(str, Enum):
    """Supported export destinations."""

    CHATGPT_PROJECT = "chatgpt_project"
    RAG_GENERIC = "rag_generic"


class ExportPackage(BaseModel):
    """A prepared bundle of chunks ready to be written to an export target.

    Attributes:
        package_id: Stable identifier for this export package.
        target: Which export destination this package is formatted for.
        company_ids: Companies included in this package.
        category: Product category included in this package, if scoped.
        chunks: The chunks included in this package. Only chunks backed by
            artifacts with an ``approved`` or ``auto_approved`` review
            status should be included here (design doc section 12).
        generated_at: Timestamp this package was assembled.
    """

    package_id: str = Field(..., description="Stable identifier for this export package.")
    target: ExportTarget = Field(..., description="Export destination this package targets.")
    company_ids: list[str] = Field(default_factory=list, description="Companies included.")
    category: str | None = Field(default=None, description="Product category scope, if any.")
    chunks: list[Chunk] = Field(
        default_factory=list, description="Chunks included in this package."
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
