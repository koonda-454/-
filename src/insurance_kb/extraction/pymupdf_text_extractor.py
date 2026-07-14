"""Text extraction and Markdown rendering using PyMuPDF (``fitz``).

Two related but distinct responsibilities live here:

1. :meth:`PyMuPdfTextExtractor.extract` implements the Phase 1
   :class:`~insurance_kb.extraction.base_extractor.BaseExtractor`
   contract — it populates a :class:`~insurance_kb.models.product.Product`'s
   ``sections`` with raw per-page text, exactly as the frozen pipeline
   interface expects.
2. :meth:`PyMuPdfTextExtractor.render_markdown` is a separate, MVP-specific
   method that produces a human-readable Markdown document (headings kept,
   tables kept where detectable, page numbers shown) plus the raw stats
   needed to build a :class:`~insurance_kb.models.qa_report.QaReport`.
   This does not fit the ``BaseExtractor`` contract (which only knows
   about ``Product``/``ProductVersion``) so it is exposed as a plain
   additional method rather than forced into that interface.

Heading detection heuristic: a line is treated as a heading if the
largest font size among its text spans is notably larger than the
document's estimated "body" font size (the most common span size across
a text-derived sample of pages) and the line is reasonably short. This is
intentionally simple — it has not been validated against a real Samsung
Fire PDF in this environment (no PyMuPDF installed, no network), so it
should be spot-checked against real output the first time this runs in
Codespaces.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import NamedTuple

from insurance_kb.core.exceptions import ExtractionException
from insurance_kb.core.logger import get_logger
from insurance_kb.extraction.base_extractor import BaseExtractor
from insurance_kb.models.product import Product, ProductSection
from insurance_kb.models.product_version import ProductVersion

logger = get_logger(__name__)

HEADING_SIZE_RATIO = 1.15  # a span must be at least this many times the body size to be a heading
HEADING_MAX_WORDS = 12  # headings are short; long lines stay body text even if in a large font


class MarkdownRenderResult(NamedTuple):
    """Output of :meth:`PyMuPdfTextExtractor.render_markdown`."""

    markdown: str
    page_count: int
    char_count: int
    table_count: int
    error_pages: list[int]


class PyMuPdfTextExtractor(BaseExtractor):
    """Extracts text (Phase 1 contract) and renders Markdown (MVP addition)."""

    def extract(self, product: Product, version: ProductVersion) -> Product:
        """See :meth:`BaseExtractor.extract`.

        Populates one :class:`~insurance_kb.models.product.ProductSection`
        per page with that page's raw extracted text.
        """
        import fitz  # local import: PyMuPDF is an opt-in dependency

        if not version.pdf_path:
            raise ExtractionException(
                "추출할 PDF 경로가 없습니다", context={"product_id": product.product_id}
            )

        try:
            doc = fitz.open(version.pdf_path)
        except Exception as exc:  # noqa: BLE001
            raise ExtractionException(
                "PDF 파일을 열 수 없습니다",
                context={"product_id": product.product_id, "pdf_path": version.pdf_path},
            ) from exc

        try:
            sections: list[ProductSection] = []
            text_pages = 0
            for page_index, page in enumerate(doc, start=1):
                text = page.get_text("text")
                if text.strip():
                    text_pages += 1
                sections.append(
                    ProductSection(
                        section_name=f"page_{page_index}", text=text, raw_pages=[page_index]
                    )
                )
            product.sections = sections
            product.extraction_method = "text"
            product.extraction_confidence = (text_pages / doc.page_count) if doc.page_count else 0.0
            return product
        finally:
            doc.close()

    def render_markdown(self, pdf_path: str | Path, title: str) -> MarkdownRenderResult:
        """Render a PDF into a human-readable Markdown document.

        Args:
            pdf_path: Path to the source PDF.
            title: Document title, used as the top-level Markdown heading.

        Returns:
            A :class:`MarkdownRenderResult` with the Markdown text and the
            raw stats needed to build a QA report.

        Raises:
            insurance_kb.core.exceptions.ExtractionException: If the PDF
                cannot be opened at all.
        """
        import fitz  # local import: PyMuPDF is an opt-in dependency

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:  # noqa: BLE001
            raise ExtractionException(
                "PDF 파일을 열 수 없습니다", context={"pdf_path": str(pdf_path)}
            ) from exc

        try:
            body_size = self._estimate_body_font_size(doc)
            lines = [f"# {title}", ""]
            char_count = 0
            table_count = 0
            error_pages: list[int] = []

            for page_index, page in enumerate(doc, start=1):
                lines.append(f"## Page {page_index}")
                lines.append("")
                try:
                    page_markdown, page_table_count = self._render_page(page, body_size)
                except Exception as exc:  # noqa: BLE001 - one bad page shouldn't abort the doc
                    logger.error(f"페이지 {page_index} 렌더링 실패: {exc}")
                    error_pages.append(page_index)
                    page_markdown = f"_(페이지 {page_index} 추출 실패: {exc})_"
                    page_table_count = 0

                table_count += page_table_count
                char_count += len(page_markdown)
                lines.append(page_markdown)
                lines.append("")

            markdown = "\n".join(lines)
            return MarkdownRenderResult(
                markdown=markdown,
                page_count=doc.page_count,
                char_count=char_count,
                table_count=table_count,
                error_pages=error_pages,
            )
        finally:
            doc.close()

    # ------------------------------------------------------------------
    # Rendering internals
    # ------------------------------------------------------------------
    @staticmethod
    def _estimate_body_font_size(doc: object, sample_pages: int = 5) -> float:
        """Estimate the document's "body text" font size, used as the
        baseline for heading detection.

        Weighted by total *character count* at each size (not span
        count): a document can have many short heading spans and few
        long body spans, so counting spans alone can misidentify a
        heading's size as the body size. Weighting by character count
        makes body paragraphs dominate, since they contain far more
        characters than headings even when there are fewer of them.
        """
        char_weight_by_size: Counter[float] = Counter()
        for page in list(doc)[:sample_pages]:
            try:
                page_dict = page.get_text("dict")
            except Exception:  # noqa: BLE001 - degrade gracefully to "no heading detection"
                continue
            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        size = round(float(span.get("size", 0)), 1)
                        span_text = span.get("text", "")
                        if size > 0 and span_text:
                            char_weight_by_size[size] += len(span_text)
        if not char_weight_by_size:
            return 0.0
        return char_weight_by_size.most_common(1)[0][0]

    def _render_page(self, page: object, body_size: float) -> tuple[str, int]:
        """Render a single page to Markdown: headings promoted where the
        font size heuristic applies, tables appended where detected."""
        heading_line_texts = self._detect_heading_lines(page, body_size)

        plain_text = page.get_text("text")
        rendered_lines: list[str] = []
        for raw_line in plain_text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                rendered_lines.append("")
                continue
            if stripped in heading_line_texts:
                rendered_lines.append(f"### {stripped}")
            else:
                rendered_lines.append(stripped)

        table_markdown_blocks, table_count = self._render_tables(page)
        body = "\n".join(rendered_lines)
        if table_markdown_blocks:
            body = body + "\n\n" + "\n\n".join(table_markdown_blocks)
        return body, table_count

    @staticmethod
    def _detect_heading_lines(page: object, body_size: float) -> set[str]:
        """Return the set of line texts on this page that look like headings."""
        headings: set[str] = set()
        if body_size <= 0:
            return headings
        try:
            page_dict = page.get_text("dict")
        except Exception:  # noqa: BLE001
            return headings

        for block in page_dict.get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                line_text = "".join(s.get("text", "") for s in spans).strip()
                if not line_text or len(line_text.split()) > HEADING_MAX_WORDS:
                    continue
                max_size = max((s.get("size", 0) for s in spans), default=0)
                if max_size >= body_size * HEADING_SIZE_RATIO:
                    headings.add(line_text)
        return headings

    @staticmethod
    def _render_tables(page: object) -> tuple[list[str], int]:
        """Detect and render tables on a page as Markdown pipe tables.

        Best-effort: relies on PyMuPDF's ``find_tables()`` (recent
        versions only); returns no tables rather than raising if the API
        isn't available or detection fails.
        """
        find_tables = getattr(page, "find_tables", None)
        if find_tables is None:
            return [], 0

        try:
            found = find_tables()
            tables = list(getattr(found, "tables", []))
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Table detection failed, skipping: {exc}")
            return [], 0

        blocks: list[str] = []
        for table in tables:
            try:
                rows = table.extract()
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Table extraction failed for a detected table, skipping: {exc}")
                continue
            if not rows:
                continue
            blocks.append(_rows_to_markdown_table(rows))
        return blocks, len(blocks)


def _rows_to_markdown_table(rows: list[list[object]]) -> str:
    """Render a list of row lists (as returned by PyMuPDF's Table.extract())
    into a Markdown pipe table."""
    normalized = [
        [("" if cell is None else str(cell)).replace("|", "\\|") for cell in row] for row in rows
    ]
    header, *body_rows = normalized
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body_rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)
