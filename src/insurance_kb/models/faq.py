"""Domain model representing a single question/answer FAQ pair, with
traceability back to the canonical field or source page it was grounded in."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FAQAudience(str, Enum):
    """Intended audience for a given FAQ pair."""

    CUSTOMER = "customer"
    AGENT = "agent"


class FAQ(BaseModel):
    """A single grounded question/answer pair.

    This is typically nested inside a
    :class:`~insurance_kb.models.knowledge_artifact.KnowledgeArtifact` of
    type ``customer_faq`` or ``agent_faq``, but is modeled independently so
    it can also be used directly by chunking and export logic.

    Attributes:
        question: The FAQ question text.
        answer: The FAQ answer text.
        audience: Whether this FAQ targets end customers or agents.
        source_field: Canonical schema field this answer was grounded in,
            e.g. ``"canonical.가입연령"``.
        source_pages: Source PDF page numbers backing this answer.
    """

    question: str = Field(..., description="The FAQ question text.")
    answer: str = Field(..., description="The FAQ answer text.")
    audience: FAQAudience = Field(default=FAQAudience.CUSTOMER)
    source_field: str | None = Field(
        default=None, description="Canonical schema field this answer was grounded in."
    )
    source_pages: list[int] = Field(
        default_factory=list, description="Backing source page numbers."
    )
