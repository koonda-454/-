"""Domain model representing a single insurance product and its raw,
company-specific structured sections (pre-standardization)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ProductSection(BaseModel):
    """A single named section extracted from a product's source document.

    Attributes:
        section_name: Section label (e.g. ``"가입연령"``, ``"보장내용"``).
        text: Extracted text content of the section.
        raw_pages: Page numbers in the source PDF this section was found on.
    """

    section_name: str = Field(..., description="Section label, e.g. '가입연령'.")
    text: str = Field(..., description="Extracted text content of the section.")
    raw_pages: list[int] = Field(
        default_factory=list, description="Source PDF page numbers for this section."
    )


class Product(BaseModel):
    """A single insurance product as structured from its source PDF.

    This model represents the *company-specific raw schema* (design doc
    section 9-1), i.e. the output of the Processing/Structuring layer,
    before standardization to :class:`~insurance_kb.models.canonical_product.CanonicalProduct`.

    Attributes:
        product_id: Stable identifier, e.g. ``"samsung_fire_health_001"``.
        company_id: Identifier of the owning :class:`Company`.
        category: Product category, e.g. ``"건강보험"``.
        product_name: Official product name.
        version: Monotonically increasing version number for this product.
        publish_date: Date the product document was published/revised.
        source_url: URL the source document was collected from.
        source_file: Path to the downloaded source PDF.
        sections: Named sections extracted from the source document.
        extraction_method: How text was obtained (``"text"`` or ``"ocr"``).
        extraction_confidence: Confidence score of the extraction, 0.0-1.0.
        created_at: Timestamp this record was first created.
        updated_at: Timestamp this record was last updated.
    """

    product_id: str = Field(..., description="Stable identifier for this product.")
    company_id: str = Field(..., description="Identifier of the owning company.")
    category: str = Field(..., description="Product category, e.g. '건강보험'.")
    product_name: str = Field(..., description="Official product name.")
    version: int = Field(default=1, ge=1, description="Monotonically increasing version number.")
    publish_date: datetime | None = Field(
        default=None, description="Date the source document was published/revised."
    )
    source_url: HttpUrl | None = Field(
        default=None, description="URL the document was collected from."
    )
    source_file: str | None = Field(default=None, description="Path to the downloaded source PDF.")
    sections: list[ProductSection] = Field(
        default_factory=list, description="Named sections extracted from the source document."
    )
    extraction_method: str | None = Field(
        default=None, description="Extraction method used: 'text' or 'ocr'."
    )
    extraction_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Confidence score of the extraction."
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
