"""Tests for Pydantic domain models in :mod:`insurance_kb.models`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from insurance_kb.models.canonical_product import CanonicalFieldValue, CanonicalProduct
from insurance_kb.models.chunk import Chunk, ChunkSource
from insurance_kb.models.company import Company
from insurance_kb.models.export_package import ExportPackage, ExportTarget
from insurance_kb.models.faq import FAQ, FAQAudience
from insurance_kb.models.knowledge_artifact import ArtifactType, KnowledgeArtifact, ReviewStatus
from insurance_kb.models.metadata import Metadata, RunStatus
from insurance_kb.models.product import Product, ProductSection
from insurance_kb.models.product_version import ProductVersion


class TestMetadata:
    def test_default_status_is_success_and_counts_are_zero(self) -> None:
        metadata = Metadata(run_id="run_001")
        assert metadata.status == RunStatus.SUCCESS
        assert metadata.new_count == 0
        assert metadata.updated_count == 0
        assert metadata.error_count == 0
        assert metadata.company_id is None
        assert metadata.error_detail is None

    def test_explicit_failed_status_with_error_detail(self) -> None:
        metadata = Metadata(
            run_id="run_002",
            company_id="samsung_fire",
            status=RunStatus.FAILED,
            error_count=1,
            error_detail="crawler timeout",
        )
        assert metadata.status == RunStatus.FAILED
        assert metadata.error_detail == "crawler timeout"

    def test_negative_counts_raise_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            Metadata(run_id="run_003", new_count=-1)


class TestCompany:
    def test_valid_company(self) -> None:
        company = Company(company_id="samsung_fire", name="삼성화재")
        assert company.is_active is True
        assert company.name_en is None

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Company(name="삼성화재")  # type: ignore[call-arg]

    def test_company_is_frozen(self) -> None:
        company = Company(company_id="samsung_fire", name="삼성화재")
        with pytest.raises(ValidationError):
            company.name = "다른이름"  # type: ignore[misc]


class TestProduct:
    def test_default_version_is_one(self) -> None:
        product = Product(
            product_id="p1", company_id="samsung_fire", category="건강보험", product_name="건강보험 A"
        )
        assert product.version == 1
        assert product.sections == []

    def test_version_must_be_at_least_one(self) -> None:
        with pytest.raises(ValidationError):
            Product(
                product_id="p1",
                company_id="samsung_fire",
                category="건강보험",
                product_name="건강보험 A",
                version=0,
            )

    def test_section_round_trip(self) -> None:
        section = ProductSection(section_name="가입연령", text="15세~65세", raw_pages=[2])
        product = Product(
            product_id="p1",
            company_id="samsung_fire",
            category="건강보험",
            product_name="건강보험 A",
            sections=[section],
        )
        assert product.sections[0].section_name == "가입연령"


class TestProductVersion:
    def test_extraction_confidence_bounds(self) -> None:
        version = ProductVersion(
            version_id="v1", product_id="p1", version_no=1, file_hash="a" * 64
        )
        assert version.is_latest is True


class TestCanonicalProduct:
    def test_get_field_returns_none_when_unmapped(self) -> None:
        canonical = CanonicalProduct(
            product_id="p1", company_id="samsung_fire", category="건강보험"
        )
        assert canonical.get_field("가입연령") is None

    def test_get_field_returns_value(self) -> None:
        field_value = CanonicalFieldValue(value={"min_age": 15, "max_age": 65})
        canonical = CanonicalProduct(
            product_id="p1",
            company_id="samsung_fire",
            category="건강보험",
            canonical={"가입연령": field_value},
        )
        assert canonical.get_field("가입연령").value["min_age"] == 15

    def test_confidence_out_of_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalProduct(
                product_id="p1",
                company_id="samsung_fire",
                category="건강보험",
                field_mapping_confidence=1.5,
            )


class TestKnowledgeArtifactAndFAQ:
    def test_artifact_type_enum(self) -> None:
        artifact = KnowledgeArtifact(
            artifact_id="a1",
            product_id="p1",
            artifact_type=ArtifactType.CUSTOMER_FAQ,
            content=[{"question": "가입연령은?", "answer": "15~65세"}],
        )
        assert artifact.review_status == ReviewStatus.NEEDS_REVIEW

    def test_faq_default_audience_is_customer(self) -> None:
        faq = FAQ(question="가입연령은?", answer="15~65세")
        assert faq.audience == FAQAudience.CUSTOMER


class TestChunkAndExportPackage:
    def test_chunk_source_enum(self) -> None:
        chunk = Chunk(
            chunk_id="c1",
            product_id="p1",
            company_id="samsung_fire",
            category="건강보험",
            chunk_source=ChunkSource.AI_GENERATED,
            text="dummy",
        )
        assert chunk.chunk_source == ChunkSource.AI_GENERATED

    def test_export_package_defaults(self) -> None:
        package = ExportPackage(package_id="pkg1", target=ExportTarget.CHATGPT_PROJECT)
        assert package.chunks == []
        assert package.company_ids == []
