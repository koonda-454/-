"""Domain model for the QA Report generated after Markdown extraction,
per the MVP requirement to auto-generate a quality report alongside every
extracted document."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class QaReport(BaseModel):
    """Quality report summarizing one PDF's text extraction outcome.

    Attributes:
        pdf_path: Path to the source PDF.
        markdown_path: Path to the generated Markdown file.
        page_count: Total number of pages in the source PDF.
        extraction_rate: Fraction of pages (0.0-1.0) that yielded
            non-trivial extracted text, used as a rough proxy for overall
            extraction quality.
        char_count: Total number of extracted characters across all pages.
        table_count: Number of tables detected and rendered into the Markdown.
        needs_ocr: Carried over from :class:`~insurance_kb.models.pdf_analysis.PdfAnalysisResult`,
            surfaced here too since it directly affects extraction trustworthiness.
        error_pages: Page numbers (1-indexed) that raised an error during
            extraction and were skipped.
        recommended_parser: Carried over from the PDF analysis step.
        generated_at: Timestamp the report was generated.
    """

    pdf_path: str = Field(..., description="Path to the source PDF.")
    markdown_path: str = Field(..., description="Path to the generated Markdown file.")
    page_count: int = Field(..., ge=0)
    extraction_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of pages with usable text."
    )
    char_count: int = Field(..., ge=0, description="Total extracted character count.")
    table_count: int = Field(default=0, ge=0, description="Number of tables detected.")
    needs_ocr: bool = Field(default=False)
    error_pages: list[int] = Field(default_factory=list, description="1-indexed pages that failed.")
    recommended_parser: str = Field(..., description="Recommended processing strategy.")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
