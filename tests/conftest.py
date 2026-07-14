"""Shared pytest fixtures for the Insurance AI Knowledge Platform test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_ROOT = _PROJECT_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from insurance_kb.core.config_loader import ConfigLoader  # noqa: E402
from insurance_kb.models.company import Company  # noqa: E402


@pytest.fixture()
def project_root() -> Path:
    """Return the repository root directory."""
    return _PROJECT_ROOT


@pytest.fixture()
def config_loader(project_root: Path) -> ConfigLoader:
    """Return a :class:`ConfigLoader` pointed at the real ``config/`` directory."""
    return ConfigLoader(config_root=project_root / "config")


@pytest.fixture()
def sample_company() -> Company:
    """Return an in-memory :class:`Company` instance for use across tests."""
    return Company(
        company_id="sample_company",
        name="샘플손해보험",
        name_en="Sample Insurance Co.",
        homepage_url="https://example.com",
        disclosure_url="https://example.com/disclosure",
        is_active=True,
    )
