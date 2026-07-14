"""Dummy :class:`BaseKnowledgeBuilder` implementation used to validate the
Hello Pipeline end-to-end without calling any real LLM API."""

from __future__ import annotations

from insurance_kb.core.logger import get_logger
from insurance_kb.knowledge_builder.base_knowledge_builder import BaseKnowledgeBuilder
from insurance_kb.models.canonical_product import CanonicalProduct
from insurance_kb.models.knowledge_artifact import ArtifactType, KnowledgeArtifact, ReviewStatus

logger = get_logger(__name__)


class DummyKnowledgeBuilder(BaseKnowledgeBuilder):
    """No-op knowledge builder that logs and returns a placeholder artifact.

    Produces an artifact of type :attr:`ArtifactType.SUMMARY` to represent
    the six real generators described in the design doc; Phase 1 does not
    implement the other five, since no LLM calls are permitted yet.
    """

    artifact_type = ArtifactType.SUMMARY

    def build(self, canonical_product: CanonicalProduct) -> KnowledgeArtifact:
        """Log a running message and return a minimal placeholder artifact."""
        logger.info(
            f"[KnowledgeBuild] DummyKnowledgeBuilder Running... "
            f"(product={canonical_product.product_id})"
        )
        return KnowledgeArtifact(
            artifact_id=f"{canonical_product.product_id}_summary_v{canonical_product.version}",
            product_id=canonical_product.product_id,
            version=canonical_product.version,
            artifact_type=self.artifact_type,
            content="dummy summary content",
            model=None,
            prompt_version=None,
            review_status=ReviewStatus.NEEDS_REVIEW,
            confidence=None,
        )
