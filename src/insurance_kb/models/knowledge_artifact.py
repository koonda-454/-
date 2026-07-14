"""Domain model representing a single AI Knowledge Builder output artifact
(design doc section 9-3)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """The six AI Knowledge Builder output types defined in the design doc."""

    SUMMARY = "summary"
    SELLING_POINT = "selling_point"
    CUSTOMER_FAQ = "customer_faq"
    AGENT_FAQ = "agent_faq"
    COMPARISON = "comparison"
    REVISION_SUMMARY = "revision_summary"


class ReviewStatus(str, Enum):
    """Human-in-the-loop review state for a generated artifact."""

    AUTO_APPROVED = "auto_approved"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class KnowledgeArtifact(BaseModel):
    """A single AI-generated knowledge artifact for one product version.

    Attributes:
        artifact_id: Stable identifier for this artifact.
        product_id: Identifier of the product this artifact describes.
        version: Product version this artifact was generated from.
        artifact_type: Which of the six generator outputs this is.
        content: Generator-specific payload. For FAQ-shaped artifacts this
            is typically a list of question/answer structures; for summary
            or revision_summary it may be a single text block.
        model: Name of the LLM model used to generate this artifact.
        prompt_version: Version identifier of the prompt template used.
        review_status: Current human review state.
        confidence: Self-reported or heuristic confidence score, 0.0-1.0.
        generated_at: Timestamp this artifact was generated.
    """

    artifact_id: str = Field(..., description="Stable identifier for this artifact.")
    product_id: str = Field(..., description="Identifier of the described product.")
    version: int = Field(default=1, ge=1, description="Product version this artifact reflects.")
    artifact_type: ArtifactType = Field(..., description="Which generator output this is.")
    content: Any = Field(..., description="Generator-specific payload.")
    model: str | None = Field(default=None, description="LLM model used to generate this artifact.")
    prompt_version: str | None = Field(default=None, description="Prompt template version used.")
    review_status: ReviewStatus = Field(default=ReviewStatus.NEEDS_REVIEW)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
