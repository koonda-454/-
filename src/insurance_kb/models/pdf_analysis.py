"""Domain model for PDF structural diagnostics, produced by
:class:`~insurance_kb.extraction.pdf_analyzer.PdfAnalyzer` before any text
extraction is attempted.

This is deliberately a separate concept from
:class:`~insurance_kb.models.pdf_document_metadata.PdfDocumentMetadata`
(Phase 2, which records *download provenance*: source URL, HTTP headers,
sha256). This model instead answers "what kind of PDF is this and how
should it be processed?" — page count, text-layer presence, image-only
pages, encryption, table presence, and a recommended parsing strategy.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PdfAnalysisResult(BaseModel):
    """Structural diagnostics for a single PDF file.

    Attributes:
        file_path: Path to the analyzed PDF.
        page_count: Total number of pages.
        is_text_pdf: Whether the PDF has an extractable text layer on at
            least most pages (as opposed to being scanned/raster-only).
        is_image_pdf: Whether the PDF appears to be image/scan-only
            (little to no extractable text, despite having pages).
        needs_ocr: Whether OCR would be required to get usable text
            (mirrors ``is_image_pdf`` for this MVP's simple heuristic, but
            kept as its own field since future versions may refine this
            independently, e.g. per-page rather than whole-document).
        has_tables: Whether at least one table-like structure was
            detected on any page.
        is_encrypted: Whether the PDF is password-protected/encrypted.
        recommended_parser: A short human-readable recommendation for how
            to process this document (e.g. ``"pymupdf_text"``,
            ``"ocr_required"``).
        analyzed_at: Timestamp the analysis was performed.
    """

    file_path: str = Field(..., description="Path to the analyzed PDF.")
    page_count: int = Field(..., ge=0)
    is_text_pdf: bool = Field(..., description="Has an extractable text layer.")
    is_image_pdf: bool = Field(..., description="Appears to be scan/image-only.")
    needs_ocr: bool = Field(..., description="Whether OCR would be required.")
    has_tables: bool = Field(default=False, description="At least one table detected.")
    is_encrypted: bool = Field(default=False, description="Password-protected/encrypted.")
    recommended_parser: str = Field(..., description="Recommended processing strategy.")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
