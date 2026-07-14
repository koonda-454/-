"""Abstract interface for extractors that convert a downloaded source file
into structured text sections on a :class:`Product` (design doc section ③
Processing Layer)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from insurance_kb.models.product import Product
from insurance_kb.models.product_version import ProductVersion


class BaseExtractor(ABC):
    """Interface every text/OCR extractor implementation must satisfy.

    Implementations read the file referenced by a :class:`ProductVersion`
    and populate the parent :class:`Product`'s ``sections`` with parsed
    section text (e.g. 가입연령, 보장내용). Both plain-text-layer PDF
    extraction and OCR-based extraction should conform to this same
    interface so the pipeline can treat them interchangeably.
    """

    @abstractmethod
    def extract(self, product: Product, version: ProductVersion) -> Product:
        """Extract structured sections from a product's source file.

        Args:
            product: The product whose source file should be parsed.
            version: The specific version (and file path) to extract from.

        Returns:
            The same :class:`Product`, updated with populated ``sections``,
            ``extraction_method``, and ``extraction_confidence``.

        Raises:
            insurance_kb.core.exceptions.ExtractionException: If extraction
                fails for both text and OCR strategies.
        """
        raise NotImplementedError
