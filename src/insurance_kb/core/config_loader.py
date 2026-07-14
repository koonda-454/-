"""YAML-based configuration loading utilities.

This module centralizes how every YAML configuration file in the project
(``config/settings.yaml``, ``config/schema/canonical_schema.yaml``,
``config/companies/*.yaml``, ``resources/prompts/*.yaml``) is read and
validated so that no other module needs to know about file paths or YAML
parsing details directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from insurance_kb.core.exceptions import ConfigException
from insurance_kb.core.logger import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """Loads and caches YAML configuration files.

    The loader is intentionally storage-agnostic about *where* config files
    live beyond a configurable root directory, so tests can point it at a
    temporary directory instead of the real ``config/`` folder.

    Args:
        config_root: Root directory containing configuration files.
    """

    def __init__(self, config_root: str | Path = "config") -> None:
        self._config_root = Path(config_root)
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, relative_path: str | Path, use_cache: bool = True) -> dict[str, Any]:
        """Load a YAML file relative to the configured config root.

        Args:
            relative_path: Path relative to ``config_root``
                (e.g. ``"settings.yaml"`` or ``"companies/sample_company.yaml"``).
            use_cache: Whether to reuse a previously loaded, cached result.

        Returns:
            The parsed YAML content as a dictionary.

        Raises:
            ConfigException: If the file does not exist or contains invalid YAML.
        """
        cache_key = str(relative_path)
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        file_path = self._config_root / relative_path
        if not file_path.exists():
            raise ConfigException(
                "Configuration file not found",
                context={"path": str(file_path)},
            )

        try:
            with file_path.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            raise ConfigException(
                "Failed to parse YAML configuration file",
                context={"path": str(file_path), "error": str(exc)},
            ) from exc

        if not isinstance(content, dict):
            raise ConfigException(
                "Configuration file must contain a YAML mapping at the top level",
                context={"path": str(file_path)},
            )

        self._cache[cache_key] = content
        logger.debug(f"Loaded config file: {file_path}")
        return content

    def load_settings(self) -> dict[str, Any]:
        """Load the global ``settings.yaml`` file."""
        return self.load("settings.yaml")

    def load_canonical_schema(self) -> dict[str, Any]:
        """Load the canonical schema definition."""
        return self.load("schema/canonical_schema.yaml")

    def load_company_config(self, company_key: str) -> dict[str, Any]:
        """Load a single company's configuration file.

        Args:
            company_key: File stem of the company config
                (e.g. ``"sample_company"`` for ``companies/sample_company.yaml``).
        """
        return self.load(f"companies/{company_key}.yaml")

    def list_company_configs(self) -> list[str]:
        """Return the file stems of all available company configuration files."""
        companies_dir = self._config_root / "companies"
        if not companies_dir.exists():
            return []
        return sorted(p.stem for p in companies_dir.glob("*.yaml"))

    def clear_cache(self) -> None:
        """Clear all cached configuration content. Primarily used in tests."""
        self._cache.clear()
