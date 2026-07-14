"""Dummy :class:`BaseExtractor` implementation used to validate the Hello
Pipeline end-to-end without parsing any real PDF."""

from __future__ import annotations

from insurance_kb.core.logger import get_logger
from insurance_kb.extraction.base_extractor import BaseExtractor
from insurance_kb.models.product import Product, ProductSection
from insurance_kb.models.product_version import ProductVersion

logger = get_logger(__name__)


class DummyExtractor(BaseExtractor):
    """No-op extractor that logs and attaches a single placeholder section."""

    def extract(self, product: Product, version: ProductVersion) -> Product:
        """Log a running message and attach a placeholder section to the product."""
        logger.info(f"[Extract] DummyExtractor Running... (product={product.product_id})")
        product.sections.append(
            ProductSection(section_name="dummy_section", text="dummy extracted text", raw_pages=[1])
        )
        product.extraction_method = "text"
        product.extraction_confidence = 1.0
        return product
