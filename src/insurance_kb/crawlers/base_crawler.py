"""Abstract interface for crawlers (Collectors) that gather product listings
from an insurance company's public disclosure pages (design doc section ⑥)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from insurance_kb.models.company import Company
from insurance_kb.models.product import Product


class BaseCrawler(ABC):
    """Interface every company-specific crawler must implement.

    Implementations are responsible only for *discovering* products (name,
    category, publish date, source URL) — not for downloading or parsing
    PDF content, which belong to :class:`~insurance_kb.downloader.base_downloader.BaseDownloader`
    and :class:`~insurance_kb.extraction.base_extractor.BaseExtractor` respectively.

    Concrete implementations must respect the target site's ``robots.txt``
    and rate limits (design doc constraints); this base class does not
    enforce that itself, but callers should assume every implementation
    does so.
    """

    @abstractmethod
    def collect(self, company: Company) -> list[Product]:
        """Discover the current list of products published by a company.

        Args:
            company: The company to collect product listings for.

        Returns:
            A list of :class:`Product` instances discovered on the
            company's disclosure pages. Returned products typically have
            ``sections`` empty at this stage; population of section
            content happens in later pipeline stages.

        Raises:
            insurance_kb.core.exceptions.CrawlerException: If the site
                cannot be reached or its structure prevents collection.
        """
        raise NotImplementedError
