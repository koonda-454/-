"""Live tests: exercise real network access against the actual Samsung
Fire website. These are marked ``@pytest.mark.live`` and are excluded
from the default ``pytest`` run (see ``pyproject.toml`` ->
``addopts = "-m 'not live'"``).

Run explicitly with:
    pytest -m live tests/test_samsung_fire_live.py

Requires: real internet access, and (for the Playwright-fallback tests)
Chromium installed via ``playwright install chromium``. These tests are
intentionally conservative — they collect at most a small number of
products and do not assert on exact product names/counts, since the
site's real content changes over time.
"""

from __future__ import annotations

import pytest

from insurance_kb.crawlers.samsung_fire_crawler import DEFAULT_ENTRY_URL, SamsungFireCrawler
from insurance_kb.downloader.pdf_downloader import PdfDownloader
from insurance_kb.models.company import Company
from insurance_kb.utils import robots_util

pytestmark = pytest.mark.live


@pytest.fixture()
def samsung_fire_company() -> Company:
    return Company(
        company_id="samsung_fire",
        name="삼성화재",
        homepage_url="https://www.samsungfire.com",
        disclosure_url=DEFAULT_ENTRY_URL,
    )


class TestRobotsTxtLive:
    def test_can_fetch_real_robots_txt(self) -> None:
        robots_util.clear_cache()
        allowed = robots_util.is_allowed(DEFAULT_ENTRY_URL, "InsuranceKB-Bot/0.1")
        # We only assert the check completes without raising; the actual
        # allow/disallow outcome depends on the real (currently unknown
        # to this codebase) robots.txt content.
        assert isinstance(allowed, bool)


class TestSamsungFireCrawlerLive:
    def test_collect_returns_at_least_one_product(self, samsung_fire_company: Company) -> None:
        # api_endpoint intentionally left unset: exercises the Playwright
        # DOM-scraping fallback path against the real site.
        crawler = SamsungFireCrawler(entry_url=DEFAULT_ENTRY_URL, categories=["장기보험"])
        products = crawler.collect(samsung_fire_company)
        assert len(products) >= 1
        assert all(p.source_url for p in products)


class TestPdfDownloaderLive:
    def test_download_first_discovered_product(
        self, samsung_fire_company: Company, tmp_path
    ) -> None:
        crawler = SamsungFireCrawler(entry_url=DEFAULT_ENTRY_URL, categories=["장기보험"])
        products = crawler.collect(samsung_fire_company)
        assert products, "사전 조건: 최소 1개 상품이 수집되어야 함"

        downloader = PdfDownloader(raw_root=tmp_path)
        version = downloader.download(products[0])
        assert version.file_hash
