"""Domain model representing a product standardized into the platform's
common canonical schema, enabling cross-company comparison (design doc
section 9-2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CanonicalFieldValue(BaseModel):
    """A single standardized field value with traceability back to its source.

    Attributes:
        value: The normalized value. Can be a scalar, list, or nested
            structure depending on the field (e.g. age range dict, list of
            coverage items).
        raw_text: The original, un-normalized text this value was derived from.
        source_pages: Source PDF page numbers backing this value.
    """

    value: Any = Field(..., description="Normalized value for this canonical field.")
    raw_text: str | None = Field(
        default=None, description="Original text this value was derived from."
    )
    source_pages: list[int] = Field(
        default_factory=list, description="Backing source page numbers."
    )


class CanonicalProduct(BaseModel):
    """A product mapped into the common, cross-company canonical schema.

    Field names under ``canonical`` are intentionally kept as a free-form
    mapping (rather than fixed attributes) so the schema can evolve via
    ``config/schema/canonical_schema.yaml`` without requiring a code change
    for every new field. Well-known field keys (as of v0.2 design) include:
    가입연령, 보험기간, 납입기간, 갱신여부, 보장내용, 면책사항, 감액지급, 납입면제.

    Attributes:
        product_id: Identifier of the source :class:`~insurance_kb.models.product.Product`.
        company_id: Identifier of the owning company.
        category: Product category, used to group comparable products.
        version: Version number this canonical snapshot corresponds to.
        canonical: Mapping of canonical field name to its standardized value.
        field_mapping_confidence: Overall confidence of the mapping, 0.0-1.0.
        unmapped_fields: Canonical fields that could not be mapped for this product.
        created_at: Timestamp this canonical snapshot was produced.
    """

    product_id: str = Field(..., description="Identifier of the source product.")
    company_id: str = Field(..., description="Identifier of the owning company.")
    category: str = Field(..., description="Product category for cross-company grouping.")
    version: int = Field(default=1, ge=1, description="Version number of this canonical snapshot.")
    canonical: dict[str, CanonicalFieldValue] = Field(
        default_factory=dict, description="Mapping of canonical field name to standardized value."
    )
    field_mapping_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Overall mapping confidence."
    )
    unmapped_fields: list[str] = Field(
        default_factory=list, description="Canonical fields that could not be mapped."
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_field(self, field_name: str) -> CanonicalFieldValue | None:
        """Return a canonical field value by name, or ``None`` if unmapped.

        Args:
            field_name: Canonical field key, e.g. ``"가입연령"``.
        """
        return self.canonical.get(field_name)
