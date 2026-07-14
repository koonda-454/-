"""Mock tests: simulate HTTP responses via ``httpx.MockTransport`` so the
full download / API-collection code paths run exactly as they would in
production, without touching the real network or a real browser.

These are distinct from the Unit tests (which never construct an HTTP
client at all) and from the Live tests (which hit the real Samsung Fire
site) — this is the tier requested as "Mock Test" in the Phase 2 pilot spec.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from insurance_kb.core.exceptions import CrawlerException, DownloadException
from insurance_kb.crawlers.samsung_fire_crawler import SamsungFireCrawler
from insurance_kb.downloader.pdf_downloader import PdfDownloader
from insurance_kb.models.company import Company
from insurance_kb.models.product import Product
from insurance_kb.utils import robots_util

FAKE_PDF_BYTES = b"%PDF-1.4 fake content for testing"

PERMISSIVE_ROBOTS_TXT = "User-agent: *\nAllow: /\n"
DISALLOW_ALL_ROBOTS_TXT = "User-agent: *\nDisallow: /\n"


@pytest.fixture(autouse=True)
def _reset_robots_cache():
    robots_util.clear_cache()
    yield
    robots_util.clear_cache()


def _make_robots_client(robots_txt: str) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=robots_txt.encode("utf-8"), request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _seed_permissive_robots(url: str) -> None:
    robots_util.get_robots_parser(url, client=_make_robots_client(PERMISSIVE_ROBOTS_TXT))


def _seed_disallow_all_robots(url: str) -> None:
    robots_util.get_robots_parser(url, client=_make_robots_client(DISALLOW_ALL_ROBOTS_TXT))


class TestPdfDownloaderMock:
    def test_successful_download_writes_pdf_and_metadata(self, tmp_path: Path) -> None:
        source_url = "https://www.samsungfire.com/download/product/P_1.pdf"
        _seed_permissive_robots(source_url)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                content=FAKE_PDF_BYTES,
                headers={
                    "content-type": "application/pdf",
                    "content-length": str(len(FAKE_PDF_BYTES)),
                    "etag": '"abc123"',
                    "last-modified": "Wed, 01 Jul 2026 00:00:00 GMT",
                },
                request=request,
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        downloader = PdfDownloader(raw_root=tmp_path, http_client=client)
        product = Product(
            product_id="samsung_fire_health_001",
            company_id="samsung_fire",
            category="건강보험",
            product_name="마이핏1640",
            source_url=source_url,
        )

        version = downloader.download(product)

        assert Path(version.pdf_path).exists()
        assert Path(version.pdf_path).read_bytes() == FAKE_PDF_BYTES
        assert Path(version.json_path).exists()
        assert version.file_hash and len(version.file_hash) == 64

    def test_skip_on_304_not_modified(self, tmp_path: Path) -> None:
        source_url = "https://www.samsungfire.com/download/product/P_2.pdf"
        _seed_permissive_robots(source_url)

        product = Product(
            product_id="samsung_fire_health_002",
            company_id="samsung_fire",
            category="건강보험",
            product_name="마이핏1640B",
            source_url=source_url,
        )

        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            if call_count["n"] == 1:
                return httpx.Response(
                    200,
                    content=FAKE_PDF_BYTES,
                    headers={"content-type": "application/pdf", "etag": '"same-etag"'},
                    request=request,
                )
            assert request.headers.get("if-none-match") == '"same-etag"'
            return httpx.Response(304, content=b"", request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        downloader = PdfDownloader(raw_root=tmp_path, http_client=client)

        first = downloader.download(product)
        second = downloader.download(product)

        assert first.file_hash == second.file_hash
        assert call_count["n"] == 2

    def test_skip_on_identical_sha256_without_conditional_headers(self, tmp_path: Path) -> None:
        source_url = "https://www.samsungfire.com/download/product/P_3.pdf"
        _seed_permissive_robots(source_url)

        product = Product(
            product_id="samsung_fire_health_003",
            company_id="samsung_fire",
            category="건강보험",
            product_name="마이핏1640C",
            source_url=source_url,
        )

        def handler(request: httpx.Request) -> httpx.Response:
            # No etag/last-modified ever returned, forcing the sha256 fallback path.
            return httpx.Response(
                200,
                content=FAKE_PDF_BYTES,
                headers={"content-type": "application/pdf"},
                request=request,
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        downloader = PdfDownloader(raw_root=tmp_path, http_client=client)

        first = downloader.download(product)
        first_mtime = Path(first.pdf_path).stat().st_mtime
        second = downloader.download(product)
        second_mtime = Path(second.pdf_path).stat().st_mtime

        assert first.file_hash == second.file_hash
        assert first_mtime == second_mtime  # file was NOT rewritten on the second call

    def test_non_200_status_raises_download_exception(self, tmp_path: Path) -> None:
        source_url = "https://www.samsungfire.com/download/product/P_missing.pdf"
        _seed_permissive_robots(source_url)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, content=b"not found", request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        downloader = PdfDownloader(raw_root=tmp_path, http_client=client)
        product = Product(
            product_id="samsung_fire_health_004",
            company_id="samsung_fire",
            category="건강보험",
            product_name="없는상품",
            source_url=source_url,
        )

        with pytest.raises(DownloadException):
            downloader.download(product)

    def test_missing_source_url_raises_download_exception(self, tmp_path: Path) -> None:
        downloader = PdfDownloader(raw_root=tmp_path)
        product = Product(
            product_id="samsung_fire_health_005",
            company_id="samsung_fire",
            category="건강보험",
            product_name="URL없는상품",
        )
        with pytest.raises(DownloadException):
            downloader.download(product)

    def test_robots_disallow_raises_download_exception(self, tmp_path: Path) -> None:
        source_url = "https://blocked.samsungfire.example/download/product/P_x.pdf"
        _seed_disallow_all_robots(source_url)

        downloader = PdfDownloader(raw_root=tmp_path)
        product = Product(
            product_id="samsung_fire_health_006",
            company_id="samsung_fire",
            category="건강보험",
            product_name="차단된상품",
            source_url=source_url,
        )
        with pytest.raises(DownloadException):
            downloader.download(product)


class TestSamsungFireCrawlerApiMock:
    def test_collect_via_api_paginates_across_categories(self) -> None:
        entry_url = "https://www.samsungfire.com/vh/page/VH.HPIF0103.do"
        api_url = "https://www.samsungfire.com/api/mock/products"
        _seed_permissive_robots(entry_url)

        pages_served: dict[str, int] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            category = request.url.split("category=")[1].split("&")[0]
            page = int(request.url.split("page=")[1].split("&")[0])
            key = f"{category}:{page}"
            pages_served[key] = pages_served.get(key, 0) + 1

            if page == 1:
                body = {
                    "items": [
                        {
                            "title": f"{category} 상품 A",
                            "productCategory": category,
                            "productDay": "2024-01-01",
                            "summaryUrl": f"https://x/download/{category}_A.pdf",
                        }
                    ],
                    "hasNext": True,
                }
            else:
                body = {
                    "items": [
                        {
                            "title": f"{category} 상품 B",
                            "productCategory": category,
                            "productDay": "2024-02-01",
                            "summaryUrl": f"https://x/download/{category}_B.pdf",
                        }
                    ],
                    "hasNext": False,
                }
            import json as _json

            return httpx.Response(200, content=_json.dumps(body).encode("utf-8"), request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        crawler = SamsungFireCrawler(
            entry_url=entry_url,
            api_endpoint=api_url,
            categories=["장기보험", "일반보험"],
            http_client=client,
        )
        company = Company(company_id="samsung_fire", name="삼성화재")

        products = crawler.collect(company)

        assert len(products) == 4  # 2 categories x 2 pages each
        names = {p.product_name for p in products}
        assert "장기보험 상품 A" in names
        assert "일반보험 상품 B" in names

    def test_collect_raises_when_robots_disallows(self) -> None:
        entry_url = "https://blocked.samsungfire.example/vh/page/VH.HPIF0103.do"
        _seed_disallow_all_robots(entry_url)

        crawler = SamsungFireCrawler(entry_url=entry_url, api_endpoint="https://x/api")
        company = Company(company_id="samsung_fire", name="삼성화재")

        with pytest.raises(CrawlerException):
            crawler.collect(company)
