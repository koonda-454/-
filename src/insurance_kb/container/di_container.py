"""Dependency injection container wiring stage interfaces to concrete
implementations (design doc section ⑥ Dependency Injection requirement).

The container is the *only* place in the codebase that knows which
concrete class implements each interface (:class:`BaseCrawler`,
:class:`BaseDownloader`, ``Storage``, ``LLM`` client, etc.). Everything
else — most importantly
:class:`~insurance_kb.orchestration.pipeline_runner.PipelineRunner` —
depends only on the abstract interfaces and receives concrete instances
through constructor injection. Swapping an implementation (e.g. going
from dummy stages to real Samsung Fire stages, or from local storage to
S3 storage) therefore only requires changing this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from insurance_kb.crawlers.base_crawler import BaseCrawler
from insurance_kb.downloader.base_downloader import BaseDownloader
from insurance_kb.export.base_exporter import BaseExporter
from insurance_kb.extraction.base_extractor import BaseExtractor
from insurance_kb.knowledge_builder.base_knowledge_builder import BaseKnowledgeBuilder
from insurance_kb.models.product import Product
from insurance_kb.orchestration.dummy.dummy_collector import DummyCollector
from insurance_kb.orchestration.dummy.dummy_downloader import DummyDownloader
from insurance_kb.orchestration.dummy.dummy_exporter import DummyExporter
from insurance_kb.orchestration.dummy.dummy_extractor import DummyExtractor
from insurance_kb.orchestration.dummy.dummy_knowledge_builder import DummyKnowledgeBuilder
from insurance_kb.orchestration.dummy.dummy_standardizer import DummyStandardizer
from insurance_kb.repositories.base_repository import BaseRepository
from insurance_kb.repositories.in_memory_product_repository import InMemoryProductRepository
from insurance_kb.standardization.base_standardizer import BaseStandardizer
from insurance_kb.storage.base_storage import BaseStorage
from insurance_kb.storage.local_file_storage import LocalFileStorage


@dataclass
class DIContainer:
    """Holds and constructs the concrete implementation for every stage interface.

    Attributes:
        crawler: Concrete :class:`BaseCrawler` implementation to use.
        downloader: Concrete :class:`BaseDownloader` implementation to use.
        extractor: Concrete :class:`BaseExtractor` implementation to use.
        standardizer: Concrete :class:`BaseStandardizer` implementation to use.
        knowledge_builder: Concrete :class:`BaseKnowledgeBuilder` implementation to use.
        exporter: Concrete :class:`BaseExporter` implementation to use.
        storage: Concrete :class:`BaseStorage` implementation to use.
            Not yet consumed by :class:`~insurance_kb.orchestration.pipeline_runner.PipelineRunner`
            in Phase 1 (Hello Pipeline only exercises the six stage
            interfaces below); reserved for Phase 2+ (raw file persistence).
        product_repository: Concrete :class:`BaseRepository` implementation
            for products. Likewise not yet consumed by ``PipelineRunner``
            in Phase 1; reserved for Phase 3+ (Metadata DB integration).
    """

    crawler: BaseCrawler = field(default_factory=DummyCollector)
    downloader: BaseDownloader = field(default_factory=DummyDownloader)
    extractor: BaseExtractor = field(default_factory=DummyExtractor)
    standardizer: BaseStandardizer = field(default_factory=DummyStandardizer)
    knowledge_builder: BaseKnowledgeBuilder = field(default_factory=DummyKnowledgeBuilder)
    exporter: BaseExporter = field(default_factory=DummyExporter)
    storage: BaseStorage = field(default_factory=LocalFileStorage)
    product_repository: BaseRepository[Product] = field(
        default_factory=InMemoryProductRepository
    )

    @classmethod
    def build_default(cls) -> "DIContainer":
        """Construct the default Phase 1 container, wired entirely with
        dummy stage implementations plus a real local storage backend.

        Returns:
            A :class:`DIContainer` ready to build a Hello Pipeline
            :class:`~insurance_kb.orchestration.pipeline_runner.PipelineRunner`.
        """
        return cls()
