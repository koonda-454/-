"""Dummy :class:`BaseDownloader` implementation used to validate the Hello
Pipeline end-to-end without downloading any real file."""

from __future__ import annotations

from insurance_kb.core.logger import get_logger
from insurance_kb.downloader.base_downloader import BaseDownloader
from insurance_kb.models.product import Product
from insurance_kb.models.product_version import ProductVersion

logger = get_logger(__name__)


class DummyDownloader(BaseDownloader):
    """No-op downloader that logs and returns a placeholder version record."""

    def download(self, product: Product) -> ProductVersion:
        """Log a running message and return a placeholder product version."""
        logger.info(f"[Download] DummyDownloader Running... (product={product.product_id})")
        return ProductVersion(
            version_id=f"{product.product_id}_v{product.version}",
            product_id=product.product_id,
            version_no=product.version,
            file_hash="0" * 64,
            pdf_path=None,
        )
