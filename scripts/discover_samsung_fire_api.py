#!/usr/bin/env python3
"""One-time reconnaissance tool: inspect Network/XHR/Fetch traffic on the
Samsung Fire 상품공시 page to determine whether a JSON API backs the
product table (per Phase 2 pilot requirement #1 — Playwright is for
*analysis*, not for driving primary data collection).

This script is deliberately NOT part of the crawling pipeline. It:
  1. Launches a real browser via Playwright.
  2. Records every XHR/fetch response while the page loads and while each
     category tab is clicked.
  3. Writes a JSON report to
     ``data/analysis/samsung_fire_network_trace.json`` for a human to review.

If the report reveals a JSON endpoint that returns the product list, set
``api_endpoint`` in ``config/companies/samsung_fire.yaml`` to that URL —
``SamsungFireCrawler`` will then use ``httpx`` exclusively and never
launch Playwright again for normal runs. If no such endpoint exists (the
table is only ever assembled server-side into rendered HTML fragments),
leave ``api_endpoint`` unset; the crawler falls back to Playwright DOM
scraping.

Usage:
    python scripts/discover_samsung_fire_api.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from insurance_kb.core.logger import configure_logging, get_logger  # noqa: E402

logger = get_logger(__name__)

ENTRY_URL = "https://www.samsungfire.com/vh/page/VH.HPIF0103.do"
CATEGORIES = ["자동차보험", "장기보험", "일반보험", "퇴직연금", "퇴직보험"]
REPORT_PATH = Path("data/analysis/samsung_fire_network_trace.json")

# Response content-types worth recording in full; everything else (images,
# fonts, css, tracking pixels) is noise for this specific investigation.
INTERESTING_CONTENT_TYPES = ("application/json", "text/json", "application/x-javascript")


def main() -> None:
    configure_logging()

    from playwright.sync_api import sync_playwright

    captured: list[dict[str, object]] = []

    def on_response(response) -> None:  # noqa: ANN001 - playwright Response type
        content_type = response.headers.get("content-type", "")
        if not any(ct in content_type for ct in INTERESTING_CONTENT_TYPES):
            return
        entry: dict[str, object] = {
            "url": response.url,
            "method": response.request.method,
            "status": response.status,
            "content_type": content_type,
        }
        try:
            body_text = response.text()
            entry["body_preview"] = body_text[:2000]
        except Exception as exc:  # noqa: BLE001 - some responses aren't readable (e.g. redirects)
            entry["body_preview"] = f"<unreadable: {exc}>"
        captured.append(entry)
        logger.info(
            f"XHR/Fetch captured: {response.request.method} {response.url} -> {response.status}"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.on("response", on_response)

            logger.info(f"진입 페이지 접속: {ENTRY_URL}")
            page.goto(ENTRY_URL, wait_until="networkidle")

            for category in CATEGORIES:
                logger.info(f"카테고리 탭 클릭 시도: {category}")
                try:
                    page.get_by_text(category, exact=True).first.click()
                    page.wait_for_load_state("networkidle")
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"탭 클릭 실패, 계속 진행: {category} ({exc})")
        finally:
            browser.close()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "entry_url": ENTRY_URL,
        "captured_at": datetime.utcnow().isoformat(),
        "response_count": len(captured),
        "responses": captured,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"분석 결과 저장: {REPORT_PATH} (JSON 응답 {len(captured)}건 캡처)")
    if not captured:
        logger.info(
            "JSON 기반 API 응답을 찾지 못했습니다. 서버사이드 렌더링일 가능성이 높으며, "
            "SamsungFireCrawler는 Playwright DOM 스크래핑 폴백 경로를 사용해야 합니다."
        )


if __name__ == "__main__":
    main()
