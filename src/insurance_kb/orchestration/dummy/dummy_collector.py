"""Dummy :class:`BaseCrawler` implementation used to validate the Hello
Pipeline end-to-end without contacting any real insurer website."""

from __future__ import annotations

from insurance_kb.core.logger import get_logger
from insurance_kb.crawlers.base_crawler import BaseCrawler
from insurance_kb.models.company import Company
from insurance_kb.models.product import Product

logger = get_logger(__name__)


class DummyCollector(BaseCrawler):
    """No-op crawler that logs and returns a single placeholder product.

    This implementation never performs network access; it exists purely
    to prove that :class:`~insurance_kb.orchestration.pipeline_runner.PipelineRunner`
    can invoke a :class:`BaseCrawler` implementation end-to-end.
    """

    def collect(self, company: Company) -> list[Product]:
        """Log a running message and return a single placeholder product."""
        logger.info(f"[Collect] DummyCollector Running... (company={company.company_id})")
        placeholder_product = Product(
            product_id=f"{company.company_id}_dummy_product_001",
            company_id=company.company_id,
            category="dummy_category",
            product_name="Dummy Product",
        )
        return [placeholder_product]
