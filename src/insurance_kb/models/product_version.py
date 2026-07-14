"""Domain model representing a single tracked version of a product's
source document, used for change detection and revision history."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProductVersion(BaseModel):
    """A single historical version of a product's source document.

    This corresponds to a row in the ``product_versions`` metadata table
    (design doc section 10) and is the unit that change detection
    (design doc section 7) operates on.

    Attributes:
        version_id: Stable identifier for this specific version record.
        product_id: Identifier of the parent :class:`~insurance_kb.models.product.Product`.
        version_no: Sequential version number, starting at 1.
        file_hash: SHA-256 hash of the source PDF, used for change detection.
        publish_date: Publish/revision date as reported by the source site.
        collected_at: Timestamp this version was collected by the crawler.
        pdf_path: Path to the archived original PDF for this version.
        json_path: Path to the structured JSON produced for this version.
        is_latest: Whether this is currently the latest known version.
    """

    version_id: str = Field(..., description="Stable identifier for this version record.")
    product_id: str = Field(..., description="Identifier of the parent product.")
    version_no: int = Field(..., ge=1, description="Sequential version number.")
    file_hash: str = Field(..., description="SHA-256 hash of the source PDF.")
    publish_date: datetime | None = Field(default=None, description="Publish/revision date.")
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    pdf_path: str | None = Field(default=None, description="Path to the archived original PDF.")
    json_path: str | None = Field(default=None, description="Path to the structured JSON.")
    is_latest: bool = Field(default=True, description="Whether this is the latest known version.")
