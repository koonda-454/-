"""Unit tests: pure logic only, no network, no Playwright, no filesystem
side effects beyond a pytest ``tmp_path``.

These verify the parts of :class:`SamsungFireCrawler` and
:class:`PdfDownloader` that don't require talking to anything external —
ID generation, category resolution, row-to-Product mapping, filename
conventions, and the :class:`PdfDocumentMetadata` model itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from insurance_kb.core.exceptions import CrawlerException
from insurance_kb.crawlers.samsung_fire_crawler import SamsungFireCrawler
from insurance_kb.downloader.pdf_downloader import PdfDownloader
from insurance_kb.models.company import Company
from insurance_kb.models.pdf_document_metadata import PdfDocumentMetadata
from insurance_kb.models.product import Product


@pytest.fixture()
def samsung_fire_company() -> Company:
    return Company(
        company_id="samsung_fire",
        name="삼성화재",
        homepage_url="https://www.samsungfire.com",
        disclosure_url="https://www.samsungfire.com/vh/page/VH.HPIF0103.do",
    )


class TestMakeProductId:
    def test_generates_stable_ascii_safe_slug(self) -> None:
        crawler = SamsungFireCrawler()
        pid = crawler._make_product_id("samsung_fire", "건강보험", "마이핏1640")
        assert pid  # non-empty
        assert " " not in pid

    def test_same_inputs_produce_same_id(self) -> None:
        crawler = SamsungFireCrawler()
        a = crawler._make_product_id("samsung_fire", "건강보험", "마이핏1640")
        b = crawler._make_product_id("samsung_fire", "건강보험", "마이핏1640")
        assert a == b


class TestResolveCategory:
    def test_prefers_specific_category_over_tab(self) -> None:
        crawler = SamsungFireCrawler()
        row = {"_tabCategory": "장기보험", "productCategory": "건강보험"}
        assert crawler._resolve_category(row) == "건강보험"

    def test_falls_back_to_tab_when_identical(self) -> None:
        crawler = SamsungFireCrawler()
        row = {"_tabCategory": "장기보험", "productCategory": "장기보험"}
        assert crawler._resolve_category(row) == "장기보험"

    def test_falls_back_to_tab_when_missing(self) -> None:
        crawler = SamsungFireCrawler()
        row = {"_tabCategory": "장기보험"}
        assert crawler._resolve_category(row) == "장기보험"

    def test_unclassified_when_both_missing(self) -> None:
        crawler = SamsungFireCrawler()
        assert crawler._resolve_category({}) == "미분류"


class TestRowToProduct:
    def test_valid_row_produces_product(self, samsung_fire_company: Company) -> None:
        crawler = SamsungFireCrawler()
        row = {
            "_tabCategory": "장기보험",
            "productCategory": "건강보험",
            "title": "무배당 삼성화재 건강보험 마이핏1640",
            "productDay": "2024-07-01",
            "summaryUrl": "https://www.samsungfire.com/download/product/P_P02_14_07_000_1.pdf",
        }
        product = crawler._row_to_product(samsung_fire_company, row)
        assert product.category == "건강보험"
        assert product.product_name == "무배당 삼성화재 건강보험 마이핏1640"
        assert str(product.source_url).startswith("https://www.samsungfire.com/download/")

    def test_missing_product_name_raises(self, samsung_fire_company: Company) -> None:
        crawler = SamsungFireCrawler()
        with pytest.raises(CrawlerException):
            crawler._row_to_product(samsung_fire_company, {"_tabCategory": "장기보험"})

    def test_missing_pdf_url_raises(self, samsung_fire_company: Company) -> None:
        crawler = SamsungFireCrawler()
        row = {"_tabCategory": "장기보험", "title": "PDF 없는 상품"}
        with pytest.raises(CrawlerException):
            crawler._row_to_product(samsung_fire_company, row)


class TestPdfDownloaderTargetPaths:
    def test_filename_follows_naming_convention(self, tmp_path: Path) -> None:
        downloader = PdfDownloader(raw_root=tmp_path)
        product = Product(
            product_id="samsung_fire_health_001",
            company_id="samsung_fire",
            category="건강보험",
            product_name="마이핏1640",
        )
        pdf_path, metadata_path = downloader._target_paths(product)
        assert pdf_path.name.startswith("삼성화재_마이핏1640_상품요약서_")
        assert pdf_path.suffix == ".pdf"
        assert metadata_path.name == pdf_path.stem + ".metadata.json"
        assert "SamsungFire" in str(pdf_path)
        assert "건강보험" in str(pdf_path)


class TestPdfDocumentMetadataModel:
    def test_valid_metadata(self) -> None:
        metadata = PdfDocumentMetadata(
            company="삼성화재",
            product="마이핏1640",
            category="건강보험",
            source_url="https://www.samsungfire.com/download/product/P_1.pdf",
            sha256="a" * 64,
            crawler_version="1.0.0",
            http_status=200,
            download_duration_seconds=0.42,
            file_path="data/raw/SamsungFire/건강보험/foo.pdf",
        )
        assert metadata.http_status == 200
        assert metadata.etag is None

    def test_negative_duration_raises(self) -> None:
        with pytest.raises(ValidationError):
            PdfDocumentMetadata(
                company="삼성화재",
                product="마이핏1640",
                category="건강보험",
                source_url="https://example.com/x.pdf",
                sha256="a" * 64,
                crawler_version="1.0.0",
                http_status=200,
                download_duration_seconds=-1.0,
                file_path="x.pdf",
            )
