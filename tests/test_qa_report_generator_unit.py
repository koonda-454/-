"""Unit tests for :mod:`insurance_kb.extraction.qa_report_generator`.

Pure combination logic — no PyMuPDF, no network, no filesystem beyond
``tmp_path`` for the save test.
"""

from __future__ import annotations

from insurance_kb.extraction.pymupdf_text_extractor import MarkdownRenderResult
from insurance_kb.extraction.qa_report_generator import build_qa_report, save_qa_report
from insurance_kb.models.pdf_analysis import PdfAnalysisResult
from insurance_kb.utils.file_util import read_json


def _analysis(**overrides) -> PdfAnalysisResult:
    defaults = dict(
        file_path="x.pdf",
        page_count=3,
        is_text_pdf=True,
        is_image_pdf=False,
        needs_ocr=False,
        has_tables=True,
        is_encrypted=False,
        recommended_parser="pymupdf_text_with_tables",
    )
    defaults.update(overrides)
    return PdfAnalysisResult(**defaults)


class TestBuildQaReport:
    def test_no_errors_gives_full_extraction_rate(self) -> None:
        render = MarkdownRenderResult(
            markdown="...", page_count=3, char_count=1200, table_count=2, error_pages=[]
        )
        report = build_qa_report("x.pdf", "x.md", _analysis(), render)

        assert report.extraction_rate == 1.0
        assert report.char_count == 1200
        assert report.table_count == 2
        assert report.error_pages == []
        assert report.recommended_parser == "pymupdf_text_with_tables"

    def test_error_pages_reduce_extraction_rate(self) -> None:
        render = MarkdownRenderResult(
            markdown="...", page_count=4, char_count=800, table_count=0, error_pages=[2, 4]
        )
        report = build_qa_report("x.pdf", "x.md", _analysis(page_count=4), render)

        assert report.extraction_rate == 0.5  # 2 of 4 pages succeeded
        assert report.error_pages == [2, 4]

    def test_needs_ocr_carried_over_from_analysis(self) -> None:
        render = MarkdownRenderResult(
            markdown="...", page_count=1, char_count=0, table_count=0, error_pages=[]
        )
        report = build_qa_report("x.pdf", "x.md", _analysis(needs_ocr=True, page_count=1), render)

        assert report.needs_ocr is True

    def test_save_qa_report_writes_json(self, tmp_path) -> None:
        render = MarkdownRenderResult(
            markdown="...", page_count=1, char_count=10, table_count=0, error_pages=[]
        )
        report = build_qa_report("x.pdf", "x.md", _analysis(page_count=1), render)

        output_path = tmp_path / "report.qa_report.json"
        save_qa_report(report, output_path)

        loaded = read_json(output_path)
        assert loaded["char_count"] == 10
