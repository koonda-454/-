"""Abstract interface for exporters that publish knowledge artifacts/chunks
to an external consumer (ChatGPT Project, RAG platforms) per design doc
section ⑫."""

from __future__ import annotations

from abc import ABC, abstractmethod

from insurance_kb.models.chunk import Chunk
from insurance_kb.models.export_package import ExportPackage


class BaseExporter(ABC):
    """Interface every export target implementation must satisfy.

    Implementations are expected to only include chunks whose backing
    artifact has an ``approved`` or ``auto_approved`` review status
    (design doc section ⑫), though enforcing that filter is the
    responsibility of the caller assembling the ``chunks`` list.
    """

    @abstractmethod
    def export(self, chunks: list[Chunk]) -> ExportPackage:
        """Assemble and publish an export package from a set of chunks.

        Args:
            chunks: The chunks to include in the export package.

        Returns:
            The assembled :class:`ExportPackage` describing what was exported.

        Raises:
            insurance_kb.core.exceptions.ExportException: If export
                assembly or publishing fails.
        """
        raise NotImplementedError
