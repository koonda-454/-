"""Tests verifying every Base Class is a proper abstract interface, and
that each dummy implementation satisfies its corresponding interface."""

from __future__ import annotations

import pytest

from insurance_kb.crawlers.base_crawler import BaseCrawler
from insurance_kb.downloader.base_downloader import BaseDownloader
from insurance_kb.export.base_exporter import BaseExporter
from insurance_kb.extraction.base_extractor import BaseExtractor
from insurance_kb.knowledge_builder.base_knowledge_builder import BaseKnowledgeBuilder
from insurance_kb.models.company import Company
from insurance_kb.models.product import Product
from insurance_kb.orchestration.base_pipeline import BasePipeline
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


class TestBaseClassesCannotBeInstantiated:
    """Every Base Class must be a true ABC: direct instantiation must fail."""

    @pytest.mark.parametrize(
        "base_class",
        [
            BaseCrawler,
            BaseDownloader,
            BaseExtractor,
            BaseStandardizer,
            BaseKnowledgeBuilder,
            BaseExporter,
            BaseStorage,
            BasePipeline,
            BaseRepository,
        ],
    )
    def test_cannot_instantiate_directly(self, base_class: type) -> None:
        with pytest.raises(TypeError):
            base_class()  # type: ignore[call-arg]


class TestDummyImplementationsSatisfyInterfaces:
    """Each dummy implementation must be a proper subclass of its interface
    and must be instantiable + callable without raising."""

    def test_dummy_collector(self, sample_company: Company) -> None:
        collector = DummyCollector()
        assert isinstance(collector, BaseCrawler)
        products = collector.collect(sample_company)
        assert isinstance(products, list)
        assert len(products) == 1
        assert isinstance(products[0], Product)

    def test_dummy_downloader(self, sample_company: Company) -> None:
        product = DummyCollector().collect(sample_company)[0]
        downloader = DummyDownloader()
        assert isinstance(downloader, BaseDownloader)
        version = downloader.download(product)
        assert version.product_id == product.product_id

    def test_dummy_extractor(self, sample_company: Company) -> None:
        product = DummyCollector().collect(sample_company)[0]
        version = DummyDownloader().download(product)
        extractor = DummyExtractor()
        assert isinstance(extractor, BaseExtractor)
        extracted = extractor.extract(product, version)
        assert len(extracted.sections) == 1

    def test_dummy_standardizer(self, sample_company: Company) -> None:
        product = DummyCollector().collect(sample_company)[0]
        standardizer = DummyStandardizer()
        assert isinstance(standardizer, BaseStandardizer)
        canonical = standardizer.standardize(product)
        assert canonical.product_id == product.product_id

    def test_dummy_knowledge_builder(self, sample_company: Company) -> None:
        product = DummyCollector().collect(sample_company)[0]
        canonical = DummyStandardizer().standardize(product)
        builder = DummyKnowledgeBuilder()
        assert isinstance(builder, BaseKnowledgeBuilder)
        artifact = builder.build(canonical)
        assert artifact.product_id == product.product_id

    def test_dummy_exporter(self) -> None:
        exporter = DummyExporter()
        assert isinstance(exporter, BaseExporter)
        package = exporter.export([])
        assert package.chunks == []

    def test_local_file_storage_is_base_storage(self, tmp_path: object) -> None:
        storage = LocalFileStorage(root_dir=tmp_path)  # type: ignore[arg-type]
        assert isinstance(storage, BaseStorage)
        storage.save_text("greeting.txt", "hello")
        assert storage.exists("greeting.txt")

    def test_in_memory_repository_is_base_repository(self, sample_company: Company) -> None:
        repo = InMemoryProductRepository()
        assert isinstance(repo, BaseRepository)
        product = DummyCollector().collect(sample_company)[0]
        repo.add(product)
        assert repo.get(product.product_id) is not None
        assert len(repo.list()) == 1
        assert repo.delete(product.product_id) is True
        assert repo.get(product.product_id) is None
