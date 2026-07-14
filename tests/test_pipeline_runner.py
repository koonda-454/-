"""End-to-end test for the Phase 1 "Hello Pipeline".

Verifies that Collect → Download → Extract → Standardize → Knowledge
Build → Export executes successfully using only dummy stage
implementations, with no network, PDF, or LLM access.
"""

from __future__ import annotations

from insurance_kb.container.di_container import DIContainer
from insurance_kb.export.base_exporter import BaseExporter
from insurance_kb.models.chunk import Chunk
from insurance_kb.models.company import Company
from insurance_kb.models.export_package import ExportPackage, ExportTarget
from insurance_kb.orchestration.pipeline_runner import PipelineRunner


class _RecordingExporter(BaseExporter):
    """Test double that records every chunk it was asked to export."""

    def __init__(self) -> None:
        self.exported_chunks: list[Chunk] = []

    def export(self, chunks: list[Chunk]) -> ExportPackage:
        self.exported_chunks.extend(chunks)
        return ExportPackage(
            package_id="test_export_package",
            target=ExportTarget.CHATGPT_PROJECT,
            chunks=chunks,
        )


class TestHelloPipeline:
    def test_pipeline_runs_end_to_end_with_default_container(
        self, sample_company: Company
    ) -> None:
        container = DIContainer.build_default()
        pipeline = PipelineRunner(
            crawler=container.crawler,
            downloader=container.downloader,
            extractor=container.extractor,
            standardizer=container.standardizer,
            knowledge_builder=container.knowledge_builder,
            exporter=container.exporter,
        )

        # Must complete without raising any exception.
        pipeline.run(sample_company)

    def test_pipeline_produces_and_exports_a_chunk(self, sample_company: Company) -> None:
        container = DIContainer.build_default()
        recording_exporter = _RecordingExporter()
        pipeline = PipelineRunner(
            crawler=container.crawler,
            downloader=container.downloader,
            extractor=container.extractor,
            standardizer=container.standardizer,
            knowledge_builder=container.knowledge_builder,
            exporter=recording_exporter,
        )

        pipeline.run(sample_company)

        assert len(recording_exporter.exported_chunks) == 1
        chunk = recording_exporter.exported_chunks[0]
        assert chunk.company_id == sample_company.company_id
        assert chunk.text  # non-empty placeholder content
