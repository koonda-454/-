"""Dummy :class:`BaseExporter` implementation used to validate the Hello
Pipeline end-to-end without publishing to any real export target."""

from __future__ import annotations

from insurance_kb.core.logger import get_logger
from insurance_kb.export.base_exporter import BaseExporter
from insurance_kb.models.chunk import Chunk
from insurance_kb.models.export_package import ExportPackage, ExportTarget

logger = get_logger(__name__)


class DummyExporter(BaseExporter):
    """No-op exporter that logs and returns a placeholder export package."""

    def export(self, chunks: list[Chunk]) -> ExportPackage:
        """Log a running message and return a placeholder export package."""
        logger.info(f"[Export] DummyExporter Running... (chunk_count={len(chunks)})")
        company_ids = sorted({chunk.company_id for chunk in chunks})
        return ExportPackage(
            package_id="dummy_export_package_001",
            target=ExportTarget.CHATGPT_PROJECT,
            company_ids=company_ids,
            chunks=chunks,
        )
