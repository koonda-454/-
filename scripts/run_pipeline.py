#!/usr/bin/env python3
"""CLI entry point that runs the Phase 1 "Hello Pipeline".

This is the only script in Phase 1 that actually executes anything. It
wires up a default :class:`DIContainer` (all dummy stage implementations),
constructs a :class:`PipelineRunner`, and runs it once against a single
placeholder :class:`Company` loaded from ``config/companies/sample_company.yaml``.

No real network access, PDF processing, or LLM calls occur — every stage
simply logs "Running..." per the Phase 1 scope.

Usage:
    python scripts/run_pipeline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this script directly (``python scripts/run_pipeline.py``)
# without requiring the package to be installed first.
_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from insurance_kb.container.di_container import DIContainer  # noqa: E402
from insurance_kb.core.config_loader import ConfigLoader  # noqa: E402
from insurance_kb.core.logger import configure_logging, get_logger  # noqa: E402
from insurance_kb.models.company import Company  # noqa: E402
from insurance_kb.orchestration.pipeline_runner import PipelineRunner  # noqa: E402

logger = get_logger(__name__)


def load_sample_company(config_loader: ConfigLoader) -> Company:
    """Load the single sample company config as a :class:`Company` model.

    Args:
        config_loader: The config loader to read ``companies/sample_company.yaml`` with.

    Returns:
        A validated :class:`Company` instance.
    """
    raw_config = config_loader.load_company_config("sample_company")
    return Company(**raw_config)


def main() -> None:
    """Wire up the DI container and run the Hello Pipeline once."""
    configure_logging()

    config_loader = ConfigLoader(config_root=Path(__file__).resolve().parent.parent / "config")
    company = load_sample_company(config_loader)

    container = DIContainer.build_default()
    pipeline = PipelineRunner(
        crawler=container.crawler,
        downloader=container.downloader,
        extractor=container.extractor,
        standardizer=container.standardizer,
        knowledge_builder=container.knowledge_builder,
        exporter=container.exporter,
    )

    pipeline.run(company)


if __name__ == "__main__":
    main()
