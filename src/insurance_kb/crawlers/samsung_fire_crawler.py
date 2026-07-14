"""Crawler implementation for Samsung Fire & Marine Insurance's product
disclosure room (상품공시실).

Design principles (per Phase 2 pilot revision):

1. **API-first, Playwright-as-fallback.** ``VH.HPIF0103.do`` renders its
   product table via client-side JS (confirmed by unresolved
   ``{{ item.title }}``-style template bindings in the raw HTML — see
   ``docs/samsung_fire_analysis.md``). Rather than assume Playwright must
   drive a full browser for every run, this crawler first checks whether
   a JSON API endpoint has already been *discovered and configured*
   (``config/companies/samsung_fire.yaml`` -> ``api_endpoint``), in which
   case it fetches data directly over ``httpx`` — cheaper and far more
   stable than DOM scraping. Discovering that endpoint in the first place
   is the job of the separate, one-time reconnaissance tool
   ``scripts/discover_samsung_fire_api.py`` (Playwright used *only* to
   inspect Network/XHR traffic, never to drive the primary collection
   path once an API is known).
2. **Crawler collects metadata only.** This class populates
   :class:`~insurance_kb.models.product.Product` with product name,
   category, publish date, and the PDF's ``source_url`` — it never
   downloads a PDF itself. Actual downloading is
   :class:`~insurance_kb.downloader.pdf_downloader.PdfDownloader`'s job.
3. **Category granularity is discovered, not assumed.** The site's
   top-level tabs (자동차보험/장기보험/일반보험/퇴직연금/퇴직보험) are
   *not* the same as product-facing categories like 건강보험/암보험/
   운전자보험. Whatever category value the source data actually reports
   per product row is used as-is for ``Product.category`` (see
   ``_resolve_category``), so sub-categories are reflected automatically
   if/when they exist, without hardcoding them here.

Because this environment's development sandbox has no live network
access, the exact DOM selectors and/or JSON API shape referenced below
are written defensively (config-driven, try/except-wrapped) but have
**not** been executed against the live site. They must be verified and
adjusted, if needed, the first time this crawler is actually run with
real network access — see ``docs/samsung_fire_analysis.md`` for the full
list of open questions this implementation is built to tolerate.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from insurance_kb.core.exceptions import CrawlerException
from insurance_kb.core.logger import get_logger
from insurance_kb.crawlers.base_crawler import BaseCrawler
from insurance_kb.models.company import Company
from insurance_kb.models.product import Product
from insurance_kb.utils import robots_util
from insurance_kb.utils.date_util import parse_flexible_date

logger = get_logger(__name__)

DEFAULT_USER_AGENT = "InsuranceKB-Bot/0.1 (+contact: tbd@example.com)"
DEFAULT_ENTRY_URL = "https://www.samsungfire.com/vh/page/VH.HPIF0103.do"
TARGET_DOCUMENT_LABEL = "상품요약서"


class SamsungFireCrawler(BaseCrawler):
    """Collects Samsung Fire product listings (name/category/date/PDF URL).

    Args:
        entry_url: The 보험상품공시 page URL.
        api_endpoint: A previously-discovered JSON API URL for the product
            listing, if known. When ``None``, falls back to Playwright DOM
            scraping (see :meth:`_collect_via_playwright`).
        categories: Top-level category tab labels to iterate (defaults to
            all five site categories if not overridden by config).
        include_discontinued: Whether to also collect 판매중지상품 (discontinued
            products). Defaults to ``False`` per the pilot's agreed scope.
        user_agent: User agent string used for every request and for the
            robots.txt permission check.
        request_delay_seconds: Minimum delay between requests, to respect
            the site and avoid overloading it.
    """

    def __init__(
        self,
        entry_url: str = DEFAULT_ENTRY_URL,
        api_endpoint: str | None = None,
        categories: list[str] | None = None,
        include_discontinued: bool = False,
        user_agent: str = DEFAULT_USER_AGENT,
        request_delay_seconds: float = 2.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._entry_url = entry_url
        self._api_endpoint = api_endpoint
        self._categories = categories or [
            "자동차보험",
            "장기보험",
            "일반보험",
            "퇴직연금",
            "퇴직보험",
        ]
        self._include_discontinued = include_discontinued
        self._user_agent = user_agent
        self._request_delay_seconds = request_delay_seconds
        self._client = http_client or httpx.Client(
            headers={"User-Agent": user_agent}, follow_redirects=True
        )

    def collect(self, company: Company) -> list[Product]:
        """See :meth:`BaseCrawler.collect`."""
        logger.info(f"Crawler Start (company={company.company_id})")

        if not robots_util.is_allowed(self._entry_url, self._user_agent):
            logger.error(f"robots.txt에 의해 접근이 차단되었습니다: {self._entry_url}")
            raise CrawlerException(
                "robots.txt 정책에 의해 홈페이지 접근이 차단되었습니다",
                context={"entry_url": self._entry_url},
            )

        try:
            if self._api_endpoint:
                raw_rows = self._collect_via_api()
            else:
                raw_rows = self._collect_via_playwright()
        except CrawlerException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error(f"홈페이지 접속/수집 실패: {exc}")
            raise CrawlerException(
                "삼성화재 상품공시 페이지 수집 중 오류가 발생했습니다",
                context={"entry_url": self._entry_url, "error": str(exc)},
            ) from exc

        products: list[Product] = []
        for row in raw_rows:
            try:
                product = self._row_to_product(company, row)
            except CrawlerException as exc:
                logger.error(f"상품 행 처리 실패, 건너뜀: {exc}")
                continue
            products.append(product)
            logger.info(f"상품 검색: {product.product_name} ({product.category})")

        logger.info(f"Crawler Finish (수집 상품 수={len(products)})")
        return products

    # ------------------------------------------------------------------
    # API path (preferred once an endpoint has been discovered/configured)
    # ------------------------------------------------------------------
    def _collect_via_api(self) -> list[dict[str, Any]]:
        """Fetch raw product rows from a known JSON API endpoint.

        The exact request shape (query params, pagination cursor, POST
        body) depends entirely on what ``scripts/discover_samsung_fire_api.py``
        finds at runtime; this method is intentionally written against a
        generic "list endpoint with optional `category` and `page` query
        params, returning `{"items": [...], "hasNext": bool}`" shape as a
        reasonable default, and should be adjusted to match the real
        contract once confirmed.
        """
        rows: list[dict[str, Any]] = []
        for category in self._categories:
            page = 1
            while True:
                response = self._client.get(
                    self._api_endpoint,
                    params={"category": category, "page": page, "saleStatus": "ON_SALE"},
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                items = payload.get("items", [])
                for item in items:
                    item.setdefault("_tabCategory", category)
                rows.extend(items)
                if not payload.get("hasNext"):
                    break
                page += 1
        return rows

    # ------------------------------------------------------------------
    # Playwright path (fallback DOM scraping; also the mechanism used by
    # the standalone discovery script, but here strictly for data extraction)
    # ------------------------------------------------------------------
    def _collect_via_playwright(self) -> list[dict[str, Any]]:
        """Fetch raw product rows by driving a real browser via Playwright.

        Used only when no ``api_endpoint`` is configured. Imports
        Playwright lazily so that environments/tests exercising only the
        API path never need the dependency installed.
        """
        from playwright.sync_api import sync_playwright  # local import: optional dependency

        rows: list[dict[str, Any]] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=self._user_agent)
                page.goto(self._entry_url, wait_until="networkidle")

                for category in self._categories:
                    self._select_category_tab(page, category)
                    page.wait_for_load_state("networkidle")
                    rows.extend(self._extract_rows_from_page(page, category))
            finally:
                browser.close()
        return rows

    def _select_category_tab(self, page: Any, category: str) -> None:
        """Click the given category's tab. Selector strategy: match the
        tab element by its visible text, since exact CSS classes/ids for
        the tab widget were not confirmed by static analysis."""
        try:
            page.get_by_text(category, exact=True).first.click()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"카테고리 탭 클릭 실패, 건너뜀: {category} ({exc})")

    def _extract_rows_from_page(self, page: Any, tab_category: str) -> list[dict[str, Any]]:
        """Extract product rows from the currently-rendered result table.

        Column order assumed from static analysis: 상품종류 | 상품명 |
        판매개시일 | 사업방법서 | 상품요약서 | 보험약관. The 상품요약서
        cell's link is resolved defensively: a direct ``href`` is used if
        present, otherwise a JS-triggered download is captured via
        Playwright's download interception (see ``_resolve_pdf_url``).
        """
        rows: list[dict[str, Any]] = []
        table_rows = page.locator("table tr").all()
        for tr in table_rows:
            cells = tr.locator("td").all()
            if len(cells) < 6:
                continue  # likely a header row or unrelated table
            try:
                product_category = cells[0].inner_text().strip() or tab_category
                product_name = cells[1].inner_text().strip()
                sale_date = cells[2].inner_text().strip()
                summary_cell = cells[4]
                pdf_url = self._resolve_pdf_url(page, summary_cell)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"행 파싱 실패, 건너뜀: {exc}")
                continue

            if not product_name:
                continue

            rows.append(
                {
                    "_tabCategory": tab_category,
                    "productCategory": product_category,
                    "title": product_name,
                    "productDay": sale_date,
                    "summaryUrl": pdf_url,
                }
            )
        return rows

    def _resolve_pdf_url(self, page: Any, summary_cell: Any) -> str | None:
        """Resolve the actual PDF URL for a '상품요약서' table cell.

        Tries a direct ``<a href>`` first (cheap, no interaction needed).
        Falls back to intercepting a Playwright download/popup event
        triggered by clicking the cell, reading the resolved URL, then
        discarding the download rather than saving it — the Crawler must
        not persist any file itself.
        """
        link = summary_cell.locator("a")
        if link.count() > 0:
            href = link.first.get_attribute("href")
            if href and href.lower() != "javascript:;":
                return href

        try:
            with page.expect_download(timeout=5000) as download_info:
                summary_cell.click()
            download = download_info.value
            url = download.url
            download.cancel()
            return url
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"상품요약서 링크를 확인할 수 없습니다: {exc}")
            return None

    # ------------------------------------------------------------------
    # Row -> Product mapping (shared by both collection paths)
    # ------------------------------------------------------------------
    def _resolve_category(self, row: dict[str, Any]) -> str:
        """Prefer a row-level category field over the top-level tab label,
        so real sub-categories (건강보험/암보험/운전자보험 등) surface
        automatically if the source data actually distinguishes them."""
        specific = row.get("productCategory")
        tab = row.get("_tabCategory")
        if specific and specific != tab:
            return specific
        return specific or tab or "미분류"

    def _row_to_product(self, company: Company, row: dict[str, Any]) -> Product:
        product_name = row.get("title") or row.get("productName")
        if not product_name:
            raise CrawlerException("상품명을 확인할 수 없습니다", context={"row": row})

        pdf_url = row.get("summaryUrl") or row.get("productSummaryUrl")
        if not pdf_url:
            raise CrawlerException(
                "PDF 없음: 상품요약서 링크를 찾을 수 없습니다",
                context={"product_name": product_name},
            )

        category = self._resolve_category(row)
        publish_date = None
        raw_date = row.get("productDay") or row.get("saleStartDate")
        if raw_date:
            publish_date = parse_flexible_date(str(raw_date))

        product_id = self._make_product_id(company.company_id, category, product_name)

        return Product(
            product_id=product_id,
            company_id=company.company_id,
            category=category,
            product_name=product_name,
            publish_date=publish_date,
            source_url=pdf_url,
        )

    @staticmethod
    def _make_product_id(company_id: str, category: str, product_name: str) -> str:
        import re

        slug_source = f"{company_id}_{category}_{product_name}"
        slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", slug_source).strip("_")
        return slug
