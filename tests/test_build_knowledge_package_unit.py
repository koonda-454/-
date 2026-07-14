"""Unit tests for the pure helper functions in
``scripts/build_knowledge_package.py`` (Markdown discovery, QA report
lookup, INDEX.md generation) — no PyMuPDF, no network required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_ROOT = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import build_knowledge_package as bkp  # noqa: E402

from insurance_kb.models.qa_report import QaReport  # noqa: E402
from insurance_kb.utils.file_util import write_json  # noqa: E402


@pytest.fixture()
def sample_markdown_tree(tmp_path: Path) -> tuple[Path, Path]:
    markdown_root = tmp_path / "extracted_text"
    qa_root = tmp_path / "qa_reports"
    category_dir = markdown_root / "건강보험"
    category_dir.mkdir(parents=True)
    (category_dir / "product_a.md").write_text("# Product A", encoding="utf-8")
    (category_dir / "product_b.md").write_text("# Product B", encoding="utf-8")

    qa_category_dir = qa_root / "건강보험"
    qa_category_dir.mkdir(parents=True)
    report = QaReport(
        pdf_path="x.pdf",
        markdown_path=str(category_dir / "product_a.md"),
        page_count=5,
        extraction_rate=0.8,
        char_count=1000,
        table_count=1,
        needs_ocr=False,
        error_pages=[3],
        recommended_parser="pymupdf_text",
    )
    write_json(qa_category_dir / "product_a.qa_report.json", report.model_dump(mode="json"))
    # product_b has no QA report on purpose, to test the "not found" path.

    return markdown_root, qa_root


class TestFindMarkdownFiles:
    def test_finds_all_markdown_files_recursively(self, sample_markdown_tree) -> None:
        markdown_root, _ = sample_markdown_tree
        files = bkp.find_markdown_files(markdown_root)
        names = {f.name for f in files}
        assert names == {"product_a.md", "product_b.md"}


class TestLoadQaReportFor:
    def test_loads_existing_report(self, sample_markdown_tree) -> None:
        markdown_root, qa_root = sample_markdown_tree
        md_path = markdown_root / "건강보험" / "product_a.md"
        report = bkp.load_qa_report_for(md_path, markdown_root, qa_root)
        assert report is not None
        assert report.page_count == 5
        assert report.error_pages == [3]

    def test_missing_report_returns_none(self, sample_markdown_tree) -> None:
        markdown_root, qa_root = sample_markdown_tree
        md_path = markdown_root / "건강보험" / "product_b.md"
        report = bkp.load_qa_report_for(md_path, markdown_root, qa_root)
        assert report is None


class TestBuildIndex:
    def test_index_lists_all_documents(self, sample_markdown_tree) -> None:
        markdown_root, qa_root = sample_markdown_tree
        files = bkp.find_markdown_files(markdown_root)
        entries = [(f, bkp.load_qa_report_for(f, markdown_root, qa_root)) for f in files]

        index = bkp.build_index(entries, markdown_root)

        assert "product_a.md" in index
        assert "product_b.md" in index
        assert "80%" in index  # product_a's extraction_rate rendered as percentage
        assert "QA report not found" in index  # product_b's missing report noted
