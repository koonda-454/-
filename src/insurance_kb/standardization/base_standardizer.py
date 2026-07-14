"""Abstract interface for standardizers that map a company-specific
:class:`Product` into the platform's common :class:`CanonicalProduct`
schema (design doc section ④ Standardization Layer)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from insurance_kb.models.canonical_product import CanonicalProduct
from insurance_kb.models.product import Product


class BaseStandardizer(ABC):
    """Interface every standardizer implementation must satisfy.

    Implementations translate a company's own section labels and phrasing
    into the shared canonical field set (가입연령, 보험기간, 납입기간,
    갱신여부, 보장내용, 면책사항, 감액지급, 납입면제, ...) defined in
    ``config/schema/canonical_schema.yaml``, enabling cross-company
    comparison questions.
    """

    @abstractmethod
    def standardize(self, product: Product) -> CanonicalProduct:
        """Map a company-specific product into the canonical schema.

        Args:
            product: The structured, company-specific product to standardize.

        Returns:
            A :class:`CanonicalProduct` with as many canonical fields
            populated as could be confidently mapped. Fields that cannot
            be mapped should be listed in ``unmapped_fields`` rather than
            guessed at.

        Raises:
            insurance_kb.core.exceptions.StandardizationException: If
                mapping fails in a way that prevents producing any
                canonical output at all.
        """
        raise NotImplementedError
