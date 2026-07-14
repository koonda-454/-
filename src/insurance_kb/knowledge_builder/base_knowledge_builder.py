"""Abstract interface for AI Knowledge Builder generators that turn a
standardized :class:`CanonicalProduct` into a derivative
:class:`KnowledgeArtifact` (design doc section ⑤ AI Knowledge Builder Layer)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from insurance_kb.models.canonical_product import CanonicalProduct
from insurance_kb.models.knowledge_artifact import ArtifactType, KnowledgeArtifact


class BaseKnowledgeBuilder(ABC):
    """Interface every AI Knowledge Builder generator must satisfy.

    There is one concrete implementation per artifact type (summary,
    selling_point, customer_faq, agent_faq, comparison, revision_summary),
    each grounded exclusively in the ``canonical`` fields of its input
    (and, for comparison/revision_summary, related products) to minimize
    hallucination risk (design doc section ⑬).
    """

    #: The artifact type this builder produces. Declared as an abstract
    #: property so ABCMeta actually enforces that every concrete subclass
    #: sets it (a plain, non-abstract class attribute in a subclass, e.g.
    #: ``artifact_type = ArtifactType.SUMMARY``, satisfies this override).
    #: Previously this was a bare type annotation, which ABCMeta does not
    #: enforce at all — forgetting to set it would only surface later as
    #: an AttributeError.
    @property
    @abstractmethod
    def artifact_type(self) -> ArtifactType:
        """Which of the six generator outputs this builder produces."""
        raise NotImplementedError

    @abstractmethod
    def build(self, canonical_product: CanonicalProduct) -> KnowledgeArtifact:
        """Generate a knowledge artifact from a standardized product.

        Args:
            canonical_product: The standardized product to generate from.

        Returns:
            A :class:`KnowledgeArtifact` of this builder's ``artifact_type``.

        Raises:
            insurance_kb.core.exceptions.KnowledgeBuilderException: If
                generation fails or produces output that cannot be grounded
                in the provided canonical data.
        """
        raise NotImplementedError
