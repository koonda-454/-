"""Builds a :class:`~insurance_kb.models.qa_report.QaReport` from the
outputs of :class:`~insurance_kb.extraction.pdf_analyzer.PdfAnalyzer` and
:class:`~insurance_kb.extraction.pymupdf_text_extractor.PyMuPdfTextExtractor`.

Kept as a standalone function (not a method on either of those classes)
since it purely combines their two outputs and has no PDF-reading
responsibility of its own.
"""

from __future__ import annotations

from pathlib import Path

from insurance_kb.extraction.pymupdf_text_extractor import MarkdownRenderResult
from insurance_kb.models.pdf_analysis import PdfAnalysisResult
from insurance_kb.models.qa_report import QaReport
from insurance_kb.utils.file_util import write_json


def build_qa_report(
    pdf_path: str | Path,
    markdown_path: str | Path,
    analysis: PdfAnalysisResult,
    render_result: MarkdownRenderResult,
) -> QaReport:
    """Combine analysis + rendering outputs into a single QA report.

    Args:
        pdf_path: Path to the source PDF.
        markdown_path: Path to the generated Markdown file.
        analysis: The PDF's structural diagnostics.
        render_result: The Markdown rendering outcome and its stats.

    Returns:
        A populated :class:`QaReport`.
    """
    page_count = render_result.page_count or analysis.page_count
    successful_pages = page_count - len(render_result.error_pages)
    extraction_rate = (successful_pages / page_count) if page_count else 0.0

    return QaReport(
        pdf_path=str(pdf_path),
        markdown_path=str(markdown_path),
        page_count=page_count,
        extraction_rate=round(max(0.0, min(1.0, extraction_rate)), 4),
        char_count=render_result.char_count,
        table_count=render_result.table_count,
        needs_ocr=analysis.needs_ocr,
        error_pages=render_result.error_pages,
        recommended_parser=analysis.recommended_parser,
    )


def save_qa_report(report: QaReport, output_path: str | Path) -> Path:
    """Persist a QA report as JSON.

    Args:
        report: The QA report to persist.
        output_path: Destination path for the JSON file.

    Returns:
        The resolved path the file was written to.
    """
    return write_json(output_path, report.model_dump(mode="json"))
