"""Domain model representing a single retrievable chunk of text for use in
FAQ answer generation or RAG indexing (design doc section 11)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ChunkSource(str, Enum):
    """Whether a chunk originates from the raw source document or from an
    AI Knowledge Builder artifact."""

    SOURCE = "source"
    AI_GENERATED = "ai_generated"


class Chunk(BaseModel):
    """A single retrievable text chunk with full provenance metadata.

    Attributes:
        chunk_id: Stable identifier for this chunk.
        product_id: Identifier of the product this chunk describes.
        company_id: Identifier of the owning company.
        category: Product category, used for cross-company filtering.
        chunk_source: Whether this is a source chunk or an AI-generated chunk.
        artifact_type: If ``chunk_source`` is ``ai_generated``, which
            :class:`~insurance_kb.models.knowledge_artifact.ArtifactType`
            it was derived from.
        version: Product version this chunk reflects.
        text: The chunk's text content.
        source_field: Canonical field this chunk is grounded in, if applicable.
        source_pages: Source PDF page numbers backing this chunk.
    """

    chunk_id: str = Field(..., description="Stable identifier for this chunk.")
    product_id: str = Field(..., description="Identifier of the described product.")
    company_id: str = Field(..., description="Identifier of the owning company.")
    category: str = Field(..., description="Product category for cross-company filtering.")
    chunk_source: ChunkSource = Field(..., description="Origin of this chunk's content.")
    artifact_type: str | None = Field(
        default=None, description="Source artifact type if chunk_source is ai_generated."
    )
    version: int = Field(default=1, ge=1)
    text: str = Field(..., description="The chunk's text content.")
    source_field: str | None = Field(default=None, description="Grounding canonical field, if any.")
    source_pages: list[int] = Field(
        default_factory=list, description="Backing source page numbers."
    )
