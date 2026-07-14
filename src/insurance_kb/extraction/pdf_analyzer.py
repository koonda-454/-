"""PDF structural diagnostics using PyMuPDF (``fitz``).

Runs *before* any text extraction is attempted, to answer: how many
pages, is there a real text layer, is it scanned/image-only, is OCR
needed, does it contain tables, and is it encrypted. The output feeds
both a standalone ``*.analysis.json`` metadata file (kept separate from
:class:`~insurance_kb.downloader.pdf_downloader.PdfDownloader`'s
download-provenance ``*.metadata.json``) and the recommended-parser hint
consumed by :class:`~insurance_kb.extraction.pymupdf_text_extractor.PyMuPdfTextExtractor`.
"""

from __future__ import annotations

from pathlib import Path

from insurance_kb.core.exceptions import ExtractionException
from insurance_kb.core.logger import get_logger
from insurance_kb.models.pdf_analysis import PdfAnalysisResult
from insurance_kb.utils.file_util import write_json

logger = get_logger(__name__)

# A page is considered to have a "real" text layer if it yields at least
# this many non-whitespace characters. Short heuristic, not a strict rule.
MIN_MEANINGFUL_CHARS_PER_PAGE = 20

# If at least this fraction of pages have a real text layer, the whole
# document is classified as a text PDF.
TEXT_PDF_PAGE_RATIO_THRESHOLD = 0.5


class PdfAnalyzer:
    """Analyzes a PDF's structure using PyMuPDF, without extracting full text."""

    def analyze(self, pdf_path: str | Path) -> PdfAnalysisResult:
        """Run structural diagnostics on a PDF file.

        Args:
            pdf_path: Path to the PDF file to analyze.

        Returns:
            A populated :class:`PdfAnalysisResult`.

        Raises:
            insurance_kb.core.exceptions.ExtractionException: If the file
                cannot be opened as a PDF at all (corrupt/not a PDF).
        """
        import fitz  # local import: keeps PyMuPDF an opt-in dependency

        path = Path(pdf_path)
        try:
            doc = fitz.open(str(path))
        except Exception as exc:  # noqa: BLE001 - fitz raises its own exception types
            raise ExtractionException(
                "PDF 파일을 열 수 없습니다", context={"file_path": str(path), "error": str(exc)}
            ) from exc

        try:
            is_encrypted = bool(doc.is_encrypted)
            if is_encrypted and not doc.authenticate(""):
                logger.warning(f"암호로 보호된 PDF입니다 (빈 암호로 인증 실패): {path}")
                return PdfAnalysisResult(
                    file_path=str(path),
                    page_count=doc.page_count,
                    is_text_pdf=False,
                    is_image_pdf=False,
                    needs_ocr=False,
                    has_tables=False,
                    is_encrypted=True,
                    recommended_parser="encrypted_requires_password",
                )

            page_count = doc.page_count
            text_page_count = 0
            image_only_page_count = 0
            has_tables = False

            for page in doc:
                text = page.get_text("text").strip()
                if len(text) >= MIN_MEANINGFUL_CHARS_PER_PAGE:
                    text_page_count += 1
                elif page.get_images(full=True):
                    image_only_page_count += 1

                if not has_tables:
                    has_tables = self._page_has_table(page)

            text_ratio = (text_page_count / page_count) if page_count else 0.0
            is_text_pdf = text_ratio >= TEXT_PDF_PAGE_RATIO_THRESHOLD
            is_image_pdf = (not is_text_pdf) and image_only_page_count > 0
            needs_ocr = is_image_pdf or not is_text_pdf

            recommended_parser = self._recommend_parser(needs_ocr, has_tables)

            return PdfAnalysisResult(
                file_path=str(path),
                page_count=page_count,
                is_text_pdf=is_text_pdf,
                is_image_pdf=is_image_pdf,
                needs_ocr=needs_ocr,
                has_tables=has_tables,
                is_encrypted=is_encrypted,
                recommended_parser=recommended_parser,
            )
        finally:
            doc.close()

    @staticmethod
    def _page_has_table(page: object) -> bool:
        """Best-effort table detection via PyMuPDF's ``find_tables()``.

        ``find_tables()`` was added in relatively recent PyMuPDF versions;
        wrapped defensively so older versions degrade to "no tables
        detected" instead of crashing the whole analysis.
        """
        find_tables = getattr(page, "find_tables", None)
        if find_tables is None:
            return False
        try:
            result = find_tables()
            return bool(getattr(result, "tables", None))
        except Exception as exc:  # noqa: BLE001 - table detection is best-effort
            logger.debug(f"Table detection failed for a page, skipping: {exc}")
            return False

    @staticmethod
    def _recommend_parser(needs_ocr: bool, has_tables: bool) -> str:
        if needs_ocr:
            return "ocr_required (e.g. pytesseract) - not implemented in this MVP"
        if has_tables:
            return "pymupdf_text_with_tables"
        return "pymupdf_text"

    def save_metadata(self, result: PdfAnalysisResult, output_path: str | Path) -> Path:
        """Persist an analysis result as a standalone ``*.analysis.json`` file.

        Args:
            result: The analysis result to persist.
            output_path: Destination path for the JSON file.

        Returns:
            The resolved path the file was written to.
        """
        return write_json(output_path, result.model_dump(mode="json"))
