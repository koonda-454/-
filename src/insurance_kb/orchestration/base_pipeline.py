"""Abstract interface for a top-level pipeline that orchestrates the
Collect → Download → Extract → Standardize → Knowledge Build → Export
sequence (design doc section ⑥ / ② Data Flow)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from insurance_kb.models.company import Company


class BasePipeline(ABC):
    """Interface every top-level pipeline implementation must satisfy.

    A pipeline coordinates calls to each stage's interface
    (:class:`~insurance_kb.crawlers.base_crawler.BaseCrawler`,
    :class:`~insurance_kb.downloader.base_downloader.BaseDownloader`, etc.)
    without implementing stage logic itself — stage implementations are
    injected (see :class:`~insurance_kb.container.di_container.DIContainer`)
    so the pipeline stays agnostic to whether it is running against dummy
    stages (Phase 1) or real, company-specific stages (later phases).
    """

    @abstractmethod
    def run(self, company: Company) -> None:
        """Execute the full pipeline for a single company.

        Args:
            company: The company to run the pipeline for.

        Raises:
            insurance_kb.core.exceptions.PipelineException: If pipeline
                orchestration itself fails (distinct from a single stage
                raising its own, more specific exception).
        """
        raise NotImplementedError
