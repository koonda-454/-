"""Dummy :class:`BaseStandardizer` implementation used to validate the
Hello Pipeline end-to-end without real canonical field mapping."""

from __future__ import annotations

from insurance_kb.core.logger import get_logger
from insurance_kb.models.canonical_product import CanonicalFieldValue, CanonicalProduct
from insurance_kb.models.product import Product
from insurance_kb.standardization.base_standardizer import BaseStandardizer

logger = get_logger(__name__)


class DummyStandardizer(BaseStandardizer):
    """No-op standardizer that logs and returns a placeholder canonical product."""

    def standardize(self, product: Product) -> CanonicalProduct:
        """Log a running message and return a minimal canonical product."""
        logger.info(f"[Standardize] DummyStandardizer Running... (product={product.product_id})")
        return CanonicalProduct(
            product_id=product.product_id,
            company_id=product.company_id,
            category=product.category,
            version=product.version,
            canonical={
                "가입연령": CanonicalFieldValue(
                    value={"min_age": None, "max_age": None}, raw_text="dummy", source_pages=[1]
                )
            },
            field_mapping_confidence=1.0,
            unmapped_fields=[],
        )
