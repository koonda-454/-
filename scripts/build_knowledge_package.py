#!/usr/bin/env python3
"""Bundle every generated Markdown document into a single, AI-agnostic
"Knowledge Package" folder (and a zip of it) that can be uploaded as-is
to ChatGPT Project, Claude Project, Gemini, Dify, or any other tool that
accepts plain Markdown/text files — no ChatGPT-specific structure or
naming is used.

Input:  every ``*.md`` under ``data/extracted_text/SamsungFire/``
Output: ``data/exports/knowledge_package/`` (Markdown files + INDEX.md)
        ``data/exports/knowledge_package.zip`` (the same, zipped)

Usage (run inside GitHub Codespaces, after ``analyze_and_extract.py``):
    python scripts/build_knowledge_package.py
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from insurance_kb.core.logger import configure_logging, get_logger  # noqa: E402
from insurance_kb.models.qa_report import QaReport  # noqa: E402
from insurance_kb.utils.file_util import ensure_dir, read_json  # noqa: E402

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_ROOT = PROJECT_ROOT / "data" / "extracted_text" / "SamsungFire"
QA_REPORT_ROOT = PROJECT_ROOT / "data" / "qa_reports" / "SamsungFire"
PACKAGE_DIR = PROJECT_ROOT / "data" / "exports" / "knowledge_package"
PACKAGE_ZIP = PROJECT_ROOT / "data" / "exports" / "knowledge_package"  # shutil appends .zip


def find_markdown_files(markdown_root: Path) -> list[Path]:
    """Return every Markdown file under ``markdown_root``, sorted."""
    return sorted(markdown_root.glob("**/*.md"))


def load_qa_report_for(
    markdown_path: Path, markdown_root: Path, qa_report_root: Path
) -> QaReport | None:
    """Locate and load the QA report corresponding to a Markdown file, if any."""
    relative = markdown_path.relative_to(markdown_root)
    qa_path = qa_report_root / relative.with_suffix("").with_suffix(".qa_report.json")
    if not qa_path.exists():
        return None
    try:
        return QaReport(**read_json(qa_path))
    except Exception as exc:  # noqa: BLE001 - a missing/corrupt QA report shouldn't block packaging
        logger.warning(f"QA report를 읽을 수 없습니다, 건너뜀: {qa_path} ({exc})")
        return None


def build_index(entries: list[tuple[Path, QaReport | None]], markdown_root: Path) -> str:
    """Build an INDEX.md summarizing every document included in the package."""
    lines = [
        "# Samsung Fire Insurance Product Knowledge Package",
        "",
        f"Generated: {datetime.utcnow().isoformat()}Z",
        f"Document count: {len(entries)}",
        "",
        "This package contains plain Markdown documents converted from Samsung "
        "Fire (삼성화재) product summary PDFs (상품요약서). It is intentionally "
        "provider-agnostic: upload these files to ChatGPT Project, Claude "
        "Project, Gemini, Dify, or any other tool that accepts document "
        "uploads, then ask questions such as 'What is the eligible age range?' "
        "or '가입연령은?'.",
        "",
        "## Documents",
        "",
        "| Document | Pages | Extraction Rate | Tables | OCR Needed | Error Pages |",
        "|---|---|---|---|---|---|",
    ]
    for markdown_path, qa in entries:
        relative = markdown_path.relative_to(markdown_root)
        if qa is not None:
            lines.append(
                f"| {relative} | {qa.page_count} | {qa.extraction_rate:.0%} | "
                f"{qa.table_count} | {'Yes' if qa.needs_ocr else 'No'} | "
                f"{qa.error_pages or '-'} |"
            )
        else:
            lines.append(f"| {relative} | - | - | - | - | (QA report not found) |")
    return "\n".join(lines) + "\n"


def main() -> None:
    configure_logging()

    if not MARKDOWN_ROOT.exists():
        logger.error(
            f"'{MARKDOWN_ROOT}' 디렉토리가 없습니다. "
            f"먼저 'python scripts/analyze_and_extract.py'를 실행하세요."
        )
        raise SystemExit(1)

    markdown_files = find_markdown_files(MARKDOWN_ROOT)
    if not markdown_files:
        logger.error(
            f"'{MARKDOWN_ROOT}' 아래에 Markdown 파일이 없습니다. "
            f"먼저 'python scripts/analyze_and_extract.py'를 실행하세요."
        )
        raise SystemExit(1)

    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    ensure_dir(PACKAGE_DIR)

    entries: list[tuple[Path, QaReport | None]] = []
    for markdown_path in markdown_files:
        relative = markdown_path.relative_to(MARKDOWN_ROOT)
        destination = PACKAGE_DIR / relative
        ensure_dir(destination.parent)
        shutil.copy2(markdown_path, destination)
        qa = load_qa_report_for(markdown_path, MARKDOWN_ROOT, QA_REPORT_ROOT)
        entries.append((markdown_path, qa))
        logger.info(f"패키지에 추가: {relative}")

    index_content = build_index(entries, MARKDOWN_ROOT)
    (PACKAGE_DIR / "INDEX.md").write_text(index_content, encoding="utf-8")

    zip_path = shutil.make_archive(str(PACKAGE_ZIP), "zip", root_dir=str(PACKAGE_DIR))

    logger.info(f"Knowledge Package 생성 완료: {PACKAGE_DIR} ({len(entries)}개 문서)")
    logger.info(f"압축 파일: {zip_path}")


if __name__ == "__main__":
    main()
