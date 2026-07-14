"""Mock tests for :class:`PyMuPdfTextExtractor`, using the same
fake-``fitz``-injection approach as ``test_pdf_analyzer_mock.py``.
"""

from __future__ import annotations

import sys
import types

import pytest

from insurance_kb.core.exceptions import ExtractionException
from insurance_kb.extraction.pymupdf_text_extractor import PyMuPdfTextExtractor
from insurance_kb.models.product import Product
from insurance_kb.models.product_version import ProductVersion


def _span(text: str, size: float) -> dict:
    return {"text": text, "size": size}


def _line(*spans: dict) -> dict:
    return {"spans": list(spans)}


def _block(*lines: dict) -> dict:
    return {"lines": list(lines)}


class FakeTable:
    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = rows

    def extract(self) -> list[list[str]]:
        return self._rows


class FakeTableFinder:
    def __init__(self, tables: list[FakeTable]) -> None:
        self.tables = tables


class FakePage:
    def __init__(
        self,
        text: str = "",
        text_dict: dict | None = None,
        tables: list[FakeTable] | None = None,
        raise_on_get_text: bool = False,
    ) -> None:
        self._text = text
        self._text_dict = text_dict or {"blocks": []}
        self._tables = tables or []
        self._raise_on_get_text = raise_on_get_text

    def get_text(self, mode: str = "text"):
        if self._raise_on_get_text:
            raise RuntimeError("simulated corrupt page")
        if mode == "dict":
            return self._text_dict
        return self._text

    def find_tables(self):
        return FakeTableFinder(self._tables)


class FakeDocument:
    def __init__(self, pages: list[FakePage]) -> None:
        self._pages = pages
        self.page_count = len(pages)

    def __iter__(self):
        return iter(self._pages)

    def close(self) -> None:
        pass


def install_fake_fitz(doc: FakeDocument) -> None:
    fake_module = types.ModuleType("fitz")
    fake_module.open = lambda path: doc  # type: ignore[attr-defined]
    sys.modules["fitz"] = fake_module


@pytest.fixture(autouse=True)
def _cleanup_fake_fitz():
    yield
    sys.modules.pop("fitz", None)


class TestExtractBaseExtractorContract:
    def test_extract_populates_sections_per_page(self, tmp_path) -> None:
        pages = [FakePage(text="첫 페이지 본문"), FakePage(text="둘째 페이지 본문")]
        install_fake_fitz(FakeDocument(pages))

        product = Product(
            product_id="p1", company_id="samsung_fire", category="건강보험", product_name="테스트상품"
        )
        version = ProductVersion(
            version_id="v1", product_id="p1", version_no=1, file_hash="a" * 64,
            pdf_path=str(tmp_path / "dummy.pdf"),
        )

        result = PyMuPdfTextExtractor().extract(product, version)

        assert len(result.sections) == 2
        assert result.sections[0].text == "첫 페이지 본문"
        assert result.extraction_method == "text"
        assert result.extraction_confidence == 1.0

    def test_extract_without_pdf_path_raises(self) -> None:
        product = Product(
            product_id="p1", company_id="samsung_fire", category="건강보험", product_name="테스트상품"
        )
        version = ProductVersion(version_id="v1", product_id="p1", version_no=1, file_hash="a" * 64)

        with pytest.raises(ExtractionException):
            PyMuPdfTextExtractor().extract(product, version)


class TestRenderMarkdown:
    def test_page_markers_present(self, tmp_path) -> None:
        pages = [FakePage(text="본문1"), FakePage(text="본문2")]
        install_fake_fitz(FakeDocument(pages))

        result = PyMuPdfTextExtractor().render_markdown(tmp_path / "x.pdf", title="테스트문서")

        assert "# 테스트문서" in result.markdown
        assert "## Page 1" in result.markdown
        assert "## Page 2" in result.markdown
        assert result.page_count == 2
        assert result.error_pages == []

    def test_heading_detected_by_font_size(self, tmp_path) -> None:
        heading_dict = {
            "blocks": [
                _block(_line(_span("가입연령", 20.0))),
                _block(_line(_span("만 15세부터 65세까지 가입 가능합니다.", 10.0))),
            ]
        }
        page = FakePage(
            text="가입연령\n만 15세부터 65세까지 가입 가능합니다.",
            text_dict=heading_dict,
        )
        install_fake_fitz(FakeDocument([page]))

        result = PyMuPdfTextExtractor().render_markdown(tmp_path / "x.pdf", title="문서")

        assert "### 가입연령" in result.markdown
        assert "만 15세부터 65세까지 가입 가능합니다." in result.markdown

    def test_table_rendered_as_markdown_pipe_table(self, tmp_path) -> None:
        table = FakeTable(rows=[["담보명", "지급금액"], ["암진단비", "3000만원"]])
        page = FakePage(text="보장내용", tables=[table])
        install_fake_fitz(FakeDocument([page]))

        result = PyMuPdfTextExtractor().render_markdown(tmp_path / "x.pdf", title="문서")

        assert "| 담보명 | 지급금액 |" in result.markdown
        assert "| 암진단비 | 3000만원 |" in result.markdown
        assert result.table_count == 1

    def test_error_page_recorded_without_aborting_document(self, tmp_path) -> None:
        pages = [
            FakePage(text="정상 페이지"),
            FakePage(raise_on_get_text=True),
            FakePage(text="정상 페이지 2"),
        ]
        install_fake_fitz(FakeDocument(pages))

        result = PyMuPdfTextExtractor().render_markdown(tmp_path / "x.pdf", title="문서")

        assert result.error_pages == [2]
        assert result.page_count == 3
        assert "정상 페이지" in result.markdown
        assert "정상 페이지 2" in result.markdown

    def test_corrupt_pdf_raises_extraction_exception(self, tmp_path) -> None:
        fake_module = types.ModuleType("fitz")

        def fake_open(path: str):
            raise RuntimeError("cannot open")

        fake_module.open = fake_open  # type: ignore[attr-defined]
        sys.modules["fitz"] = fake_module

        with pytest.raises(ExtractionException):
            PyMuPdfTextExtractor().render_markdown(tmp_path / "corrupt.pdf", title="문서")
