#!/usr/bin/env python3
"""Run a single company's crawler (Collector) + downloader end-to-end.

Phase 2 pilot: Samsung Fire only. Loads
``config/companies/samsung_fire.yaml``, runs :class:`SamsungFireCrawler`
to discover products (name/category/publish date/PDF URL only), then runs
:class:`PdfDownloader` to actually fetch each PDF with change detection.

This script intentionally does NOT go through
:class:`~insurance_kb.orchestration.pipeline_runner.PipelineRunner` — per
this phase's scope, OCR/standardization/knowledge building/export are all
out of bounds, so only the first two pipeline stages are wired up here.

Usage:
    python scripts/crawl.py [--company samsung_fire]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from insurance_kb.core.config_loader import ConfigLoader  # noqa: E402
from insurance_kb.core.exceptions import InsuranceKBException  # noqa: E402
from insurance_kb.core.logger import configure_logging, get_logger  # noqa: E402
from insurance_kb.crawlers.samsung_fire_crawler import (  # noqa: E402
    DEFAULT_ENTRY_URL,
    SamsungFireCrawler,
)
from insurance_kb.downloader.pdf_downloader import PdfDownloader  # noqa: E402
from insurance_kb.models.company import Company  # noqa: E402

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Only Samsung Fire is wired up in this pilot; adding another company
# means adding both a company config file and a dedicated crawler/downloader
# pairing, not modifying this mapping's shape.
_CRAWLER_FACTORY = {
    "samsung_fire": lambda cfg: SamsungFireCrawler(
        entry_url=cfg.get("crawler_settings", {}).get("entry_url", DEFAULT_ENTRY_URL),
        api_endpoint=cfg.get("crawler_settings", {}).get("api_endpoint"),
        categories=(
            [c["label"] for c in cfg.get("crawler_settings", {}).get("categories", [])] or None
        ),
        include_discontinued=cfg.get("crawler_settings", {}).get("include_discontinued", False),
        request_delay_seconds=cfg.get("crawler_settings", {}).get("request_delay_seconds", 2.0),
    ),
}

_DOWNLOADER_FACTORY = {
    "samsung_fire": lambda cfg: PdfDownloader(
        company_folder="SamsungFire",
        company_display_name=cfg.get("name", "삼성화재"),
    ),
}


def run(company_key: str) -> None:
    configure_logging()
    config_loader = ConfigLoader(config_root=PROJECT_ROOT / "config")
    cfg = config_loader.load_company_config(company_key)
    company = Company(**{k: v for k, v in cfg.items() if k in Company.model_fields})

    if company_key not in _CRAWLER_FACTORY:
        raise SystemExit(f"'{company_key}'에 대한 크롤러가 아직 구현되지 않았습니다.")

    crawler = _CRAWLER_FACTORY[company_key](cfg)
    downloader = _DOWNLOADER_FACTORY[company_key](cfg)

    try:
        products = crawler.collect(company)
    except InsuranceKBException as exc:
        logger.error(f"수집 실패: {exc}")
        raise SystemExit(1) from exc

    success_count, skip_count, error_count = 0, 0, 0
    for product in products:
        try:
            downloader.download(product)
            success_count += 1
        except InsuranceKBException as exc:
            logger.error(f"다운로드 실패: {product.product_name} ({exc})")
            error_count += 1

    logger.info(
        f"완료: 총 {len(products)}건 중 성공 {success_count}건, 오류 {error_count}건"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--company", default="samsung_fire", help="config/companies/{name}.yaml의 파일명"
    )
    args = parser.parse_args()
    run(args.company)


if __name__ == "__main__":
    main()
