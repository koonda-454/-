#!/usr/bin/env python3
"""Analyze every downloaded Samsung Fire PDF and produce, for each:
1. A structural analysis (``*.analysis.json``) via :class:`PdfAnalyzer`.
2. A human-readable Markdown document via :class:`PyMuPdfTextExtractor`.
3. A QA report (``*.qa_report.json``) summarizing extraction quality.

Input:  every ``*.pdf`` under ``data/raw/SamsungFire/`` (however many
        ``scripts/crawl.py`` downloaded — this MVP does not artificially
        limit the count).
Output: ``data/extracted_text/SamsungFire/{category}/{stem}.md``
        ``data/raw/SamsungFire/{category}/{stem}.analysis.json``
        ``data/qa_reports/SamsungFire/{category}/{stem}.qa_report.json``

OCR is intentionally NOT implemented: PDFs flagged ``needs_ocr=True`` are
still processed (whatever text PyMuPDF can extract is kept), but this is
logged clearly so it's obvious the Markdown may be incomplete for those
files.

Usage (run inside GitHub Codespaces, after ``pip install -r requirements.txt``):
    python scripts/analyze_and_extract.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from insurance_kb.core.exceptions import InsuranceKBException  # noqa: E402
from insurance_kb.core.logger import configure_logging, get_logger  # noqa: E402
from insurance_kb.extraction.pdf_analyzer import PdfAnalyzer  # noqa: E402
from insurance_kb.extraction.pymupdf_text_extractor import PyMuPdfTextExtractor  # noqa: E402
from insurance_kb.extraction.qa_report_generator import (  # noqa: E402
    build_qa_report,
    save_qa_report,
)
from insurance_kb.utils.file_util import ensure_dir  # noqa: E402

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "SamsungFire"
MARKDOWN_ROOT = PROJECT_ROOT / "data" / "extracted_text" / "SamsungFire"
QA_REPORT_ROOT = PROJECT_ROOT / "data" / "qa_reports" / "SamsungFire"


def find_pdfs(raw_root: Path) -> list[Path]:
    """Return every PDF under ``raw_root``, sorted for deterministic output."""
    return sorted(raw_root.glob("**/*.pdf"))


def process_one_pdf(pdf_path: Path, raw_root: Path) -> bool:
    """Analyze, extract, and QA-report a single PDF.

    Returns:
        ``True`` on success, ``False`` if this PDF was skipped due to an error.
    """
    category = pdf_path.parent.name
    stem = pdf_path.stem
    title = stem  # human-readable title derived from the filename convention

    analyzer = PdfAnalyzer()
    extractor = PyMuPdfTextExtractor()

    logger.info(f"분석 시작: {pdf_path.name}")
    try:
        analysis = analyzer.analyze(pdf_path)
    except InsuranceKBException as exc:
        logger.error(f"PDF 분석 실패, 건너뜀: {pdf_path.name} ({exc})")
        return False

    analysis_path = pdf_path.with_suffix("").with_suffix(".analysis.json")
    analyzer.save_metadata(analysis, analysis_path)
    logger.info(
        f"분석 완료: {pdf_path.name} "
        f"(페이지 {analysis.page_count}, 텍스트PDF={analysis.is_text_pdf}, "
        f"OCR필요={analysis.needs_ocr}, 표존재={analysis.has_tables}, "
        f"추천Parser={analysis.recommended_parser})"
    )
    if analysis.needs_ocr:
        logger.warning(
            f"이 PDF는 OCR이 필요할 수 있습니다 (이번 MVP는 OCR 미구현): {pdf_path.name}"
        )

    logger.info(f"Markdown 생성 시작: {pdf_path.name}")
    try:
        render_result = extractor.render_markdown(pdf_path, title=title)
    except InsuranceKBException as exc:
        logger.error(f"Markdown 생성 실패, 건너뜀: {pdf_path.name} ({exc})")
        return False

    markdown_dir = MARKDOWN_ROOT / category
    ensure_dir(markdown_dir)
    markdown_path = markdown_dir / f"{stem}.md"
    markdown_path.write_text(render_result.markdown, encoding="utf-8")
    logger.info(f"Markdown 생성 완료: {markdown_path}")

    qa_report = build_qa_report(pdf_path, markdown_path, analysis, render_result)
    qa_dir = QA_REPORT_ROOT / category
    ensure_dir(qa_dir)
    qa_path = qa_dir / f"{stem}.qa_report.json"
    save_qa_report(qa_report, qa_path)
    logger.info(
        f"QA Report 생성 완료: {qa_path} "
        f"(추출성공률={qa_report.extraction_rate:.0%}, 문자수={qa_report.char_count}, "
        f"표={qa_report.table_count}, 오류페이지={qa_report.error_pages})"
    )
    return True


def main() -> None:
    configure_logging()

    if not RAW_ROOT.exists():
        logger.error(
            f"'{RAW_ROOT}' 디렉토리가 없습니다. "
            f"먼저 'python scripts/crawl.py --company samsung_fire'로 PDF를 다운로드하세요."
        )
        raise SystemExit(1)

    pdfs = find_pdfs(RAW_ROOT)
    if not pdfs:
        logger.error(
            f"'{RAW_ROOT}' 아래에 PDF가 없습니다. "
            f"먼저 'python scripts/crawl.py --company samsung_fire'로 PDF를 다운로드하세요."
        )
        raise SystemExit(1)

    logger.info(f"총 {len(pdfs)}개 PDF 처리 시작")
    success_count = 0
    for pdf_path in pdfs:
        if process_one_pdf(pdf_path, RAW_ROOT):
            success_count += 1

    logger.info(f"완료: 총 {len(pdfs)}개 중 {success_count}개 성공")


if __name__ == "__main__":
    main()
