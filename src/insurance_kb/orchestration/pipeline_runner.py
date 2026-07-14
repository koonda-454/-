"""Concrete pipeline orchestration implementing the
Collect → Download → Extract → Standardize → Knowledge Build → Export
sequence (design doc section ② Data Flow / ⑥ Pipeline).

For Phase 1, this class is exercised exclusively with dummy stage
implementations (see :mod:`insurance_kb.orchestration.dummy`), proving the
sequence executes end-to-end ("Hello Pipeline") without any real network,
PDF, or LLM access. Later phases can inject real stage implementations via
:class:`~insurance_kb.container.di_container.DIContainer` without any
change to this class, since it depends only on the abstract stage
interfaces (Dependency Inversion).
"""

from __future__ import annotations

from insurance_kb.core.exceptions import PipelineException
from insurance_kb.core.logger import get_logger
from insurance_kb.crawlers.base_crawler import BaseCrawler
from insurance_kb.downloader.base_downloader import BaseDownloader
from insurance_kb.export.base_exporter import BaseExporter
from insurance_kb.extraction.base_extractor import BaseExtractor
from insurance_kb.knowledge_builder.base_knowledge_builder import BaseKnowledgeBuilder
from insurance_kb.models.chunk import Chunk, ChunkSource
from insurance_kb.models.company import Company
from insurance_kb.orchestration.base_pipeline import BasePipeline
from insurance_kb.standardization.base_standardizer import BaseStandardizer

logger = get_logger(__name__)


class PipelineRunner(BasePipeline):
    """Coordinates one full pass of the pipeline for a single company.

    All collaborators are received through the constructor (constructor
    injection) rather than being instantiated internally, keeping this
    class decoupled from any specific stage implementation.

    Args:
        crawler: Stage implementation for product collection.
        downloader: Stage implementation for source file download.
        extractor: Stage implementation for text/OCR extraction.
        standardizer: Stage implementation for canonical schema mapping.
        knowledge_builder: Stage implementation for AI artifact generation.
        exporter: Stage implementation for publishing export packages.
    """

    def __init__(
        self,
        crawler: BaseCrawler,
        downloader: BaseDownloader,
        extractor: BaseExtractor,
        standardizer: BaseStandardizer,
        knowledge_builder: BaseKnowledgeBuilder,
        exporter: BaseExporter,
    ) -> None:
        self._crawler = crawler
        self._downloader = downloader
        self._extractor = extractor
        self._standardizer = standardizer
        self._knowledge_builder = knowledge_builder
        self._exporter = exporter

    def run(self, company: Company) -> None:
        """Execute Collect → Download → Extract → Standardize → Knowledge Build → Export.

        Args:
            company: The company to run the pipeline for.

        Raises:
            insurance_kb.core.exceptions.PipelineException: If any stage
                raises an unhandled exception during orchestration.
        """
        logger.info("Pipeline Start")
        try:
            products = self._crawler.collect(company)

            for product in products:
                version = self._downloader.download(product)
                product = self._extractor.extract(product, version)
                canonical_product = self._standardizer.standardize(product)
                artifact = self._knowledge_builder.build(canonical_product)

                chunk = Chunk(
                    chunk_id=f"{artifact.artifact_id}_chunk_001",
                    product_id=product.product_id,
                    company_id=company.company_id,
                    category=product.category,
                    chunk_source=ChunkSource.AI_GENERATED,
                    artifact_type=artifact.artifact_type.value,
                    version=product.version,
                    text=str(artifact.content),
                )
                self._exporter.export([chunk])
        except Exception as exc:  # noqa: BLE001 - re-raised as a domain exception below
            logger.error(f"Pipeline Failed (company={company.company_id}): {exc}")
            raise PipelineException(
                "Pipeline execution failed", context={"company_id": company.company_id}
            ) from exc
        else:
            # Only reached when every stage above completed without raising,
            # so "Pipeline Finish" now genuinely means success. Previously
            # this log lived in a `finally` block and was printed even when
            # the pipeline failed, which could mislead readers of the logs.
            logger.info("Pipeline Finish")
