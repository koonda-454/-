"""Abstract interface for downloaders that retrieve a product's source
file (typically a PDF) and register it as a tracked version."""

from __future__ import annotations

from abc import ABC, abstractmethod

from insurance_kb.models.product import Product
from insurance_kb.models.product_version import ProductVersion


class BaseDownloader(ABC):
    """Interface every downloader implementation must satisfy.

    A downloader is responsible for fetching the raw source file for a
    :class:`Product`, computing its content hash for change detection
    (design doc section ⑦), and producing a :class:`ProductVersion`
    record describing where the file was stored.
    """

    @abstractmethod
    def download(self, product: Product) -> ProductVersion:
        """Download a product's source file and register it as a version.

        Args:
            product: The product whose ``source_url`` should be downloaded.

        Returns:
            A :class:`ProductVersion` describing the downloaded file,
            including its content hash and storage path.

        Raises:
            insurance_kb.core.exceptions.DownloadException: If the file
                cannot be retrieved or saved.
        """
        raise NotImplementedError
