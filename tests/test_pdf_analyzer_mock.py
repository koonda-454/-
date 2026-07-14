"""Mock tests for :class:`PdfAnalyzer`.

PyMuPDF (``fitz``) is imported lazily *inside* ``PdfAnalyzer.analyze()``,
so these tests inject a fake ``fitz`` module into ``sys.modules`` before
calling it — analogous to how the Phase 2 tests use
``httpx.MockTransport`` to simulate an external system without touching
the real thing. This validates the analyzer's *logic* (page counting,
text/image classification, OCR flag, table detection, encryption
handling) independent of whether PyMuPDF itself is installed.
"""

from __future__ import annotations

import sys
import types

import pytest

from insurance_kb.core.exceptions import ExtractionException
from insurance_kb.extraction.pdf_analyzer import PdfAnalyzer


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
        images: list | None = None,
        tables: list[FakeTable] | None = None,
        text_dict: dict | None = None,
    ) -> None:
        self._text = text
        self._images = images or []
        self._tables = tables
        self._text_dict = text_dict or {"blocks": []}

    def get_text(self, mode: str = "text"):
        if mode == "dict":
            return self._text_dict
        return self._text

    def get_images(self, full: bool = False):
        return self._images

    def find_tables(self):
        if self._tables is None:
            raise RuntimeError("find_tables not supported on this fake page")
        return FakeTableFinder(self._tables)


class FakePageNoFindTables(FakePage):
    """A page whose class doesn't even define find_tables (older PyMuPDF)."""

    find_tables = None  # type: ignore[assignment]


class FakeDocument:
    def __init__(
        self, pages: list[FakePage], is_encrypted: bool = False, auth_succeeds: bool = True
    ) -> None:
        self._pages = pages
        self.page_count = len(pages)
        self.is_encrypted = is_encrypted
        self._auth_succeeds = auth_succeeds
        self.closed = False

    def authenticate(self, password: str) -> bool:
        return self._auth_succeeds

    def __iter__(self):
        return iter(self._pages)

    def close(self) -> None:
        self.closed = True


def install_fake_fitz(doc: FakeDocument | None = None, raise_on_open: bool = False) -> None:
    fake_module = types.ModuleType("fitz")

    def fake_open(path: str):
        if raise_on_open:
            raise RuntimeError("cannot open, simulated corrupt file")
        return doc

    fake_module.open = fake_open  # type: ignore[attr-defined]
    sys.modules["fitz"] = fake_module


@pytest.fixture(autouse=True)
def _cleanup_fake_fitz():
    yield
    sys.modules.pop("fitz", None)


class TestPdfAnalyzer:
    def test_text_pdf_classified_correctly(self, tmp_path) -> None:
        pages = [FakePage(text="충분히 긴 본문 텍스트입니다. " * 3) for _ in range(3)]
        install_fake_fitz(FakeDocument(pages))

        result = PdfAnalyzer().analyze(tmp_path / "dummy.pdf")

        assert result.page_count == 3
        assert result.is_text_pdf is True
        assert result.is_image_pdf is False
        assert result.needs_ocr is False
        assert result.recommended_parser == "pymupdf_text"

    def test_image_only_pdf_needs_ocr(self, tmp_path) -> None:
        pages = [FakePage(text="", images=[("img1",)]) for _ in range(2)]
        install_fake_fitz(FakeDocument(pages))

        result = PdfAnalyzer().analyze(tmp_path / "scanned.pdf")

        assert result.is_text_pdf is False
        assert result.is_image_pdf is True
        assert result.needs_ocr is True
        assert result.recommended_parser.startswith("ocr_required")

    def test_encrypted_pdf_with_failed_auth(self, tmp_path) -> None:
        install_fake_fitz(FakeDocument([FakePage()], is_encrypted=True, auth_succeeds=False))

        result = PdfAnalyzer().analyze(tmp_path / "locked.pdf")

        assert result.is_encrypted is True
        assert result.recommended_parser == "encrypted_requires_password"

    def test_table_detection(self, tmp_path) -> None:
        table = FakeTable(rows=[["h1", "h2"], ["a", "b"]])
        pages = [FakePage(text="본문 텍스트가 충분히 깁니다 " * 3, tables=[table])]
        install_fake_fitz(FakeDocument(pages))

        result = PdfAnalyzer().analyze(tmp_path / "with_table.pdf")

        assert result.has_tables is True
        assert result.recommended_parser == "pymupdf_text_with_tables"

    def test_missing_find_tables_degrades_gracefully(self, tmp_path) -> None:
        pages = [FakePageNoFindTables(text="본문 텍스트가 충분히 깁니다 " * 3)]
        install_fake_fitz(FakeDocument(pages))

        result = PdfAnalyzer().analyze(tmp_path / "old_pymupdf.pdf")

        assert result.has_tables is False  # did not crash, just reported no tables

    def test_corrupt_pdf_raises_extraction_exception(self, tmp_path) -> None:
        install_fake_fitz(raise_on_open=True)

        with pytest.raises(ExtractionException):
            PdfAnalyzer().analyze(tmp_path / "corrupt.pdf")

    def test_save_metadata_writes_json(self, tmp_path) -> None:
        pages = [FakePage(text="본문 텍스트가 충분히 깁니다 " * 3)]
        install_fake_fitz(FakeDocument(pages))
        result = PdfAnalyzer().analyze(tmp_path / "dummy.pdf")

        output_path = tmp_path / "dummy.analysis.json"
        PdfAnalyzer().save_metadata(result, output_path)

        assert output_path.exists()
        assert "recommended_parser" in output_path.read_text(encoding="utf-8")
