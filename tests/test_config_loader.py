"""Tests for :class:`insurance_kb.core.config_loader.ConfigLoader`."""

from __future__ import annotations

from pathlib import Path

import pytest

from insurance_kb.core.config_loader import ConfigLoader
from insurance_kb.core.exceptions import ConfigException


class TestConfigLoaderRealFiles:
    """Tests against the real config/ files shipped with the project."""

    def test_load_settings(self, config_loader: ConfigLoader) -> None:
        settings = config_loader.load_settings()
        assert settings["project"]["name"] == "insurance-ai-knowledge-platform"
        assert "paths" in settings
        assert "logging" in settings

    def test_load_canonical_schema(self, config_loader: ConfigLoader) -> None:
        schema = config_loader.load_canonical_schema()
        assert schema["schema_version"] == "0.2.0"
        field_keys = {f["key"] for f in schema["fields"]}
        assert "가입연령" in field_keys
        assert "보장내용" in field_keys

    def test_load_sample_company_config(self, config_loader: ConfigLoader) -> None:
        company_config = config_loader.load_company_config("sample_company")
        assert company_config["company_id"] == "sample_company"
        assert company_config["is_active"] is True

    def test_list_company_configs_includes_sample(self, config_loader: ConfigLoader) -> None:
        companies = config_loader.list_company_configs()
        assert "sample_company" in companies

    def test_cache_returns_same_dict_object(self, config_loader: ConfigLoader) -> None:
        first = config_loader.load_settings()
        second = config_loader.load_settings()
        assert first is second  # cached, same object identity

    def test_clear_cache_forces_reload(self, config_loader: ConfigLoader) -> None:
        first = config_loader.load_settings()
        config_loader.clear_cache()
        second = config_loader.load_settings()
        assert first is not second
        assert first == second


class TestConfigLoaderErrorHandling:
    """Tests for failure modes using a temporary config directory."""

    def test_missing_file_raises_config_exception(self, tmp_path: Path) -> None:
        loader = ConfigLoader(config_root=tmp_path)
        with pytest.raises(ConfigException):
            loader.load("does_not_exist.yaml")

    def test_invalid_yaml_raises_config_exception(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("key: [unclosed", encoding="utf-8")
        loader = ConfigLoader(config_root=tmp_path)
        with pytest.raises(ConfigException):
            loader.load("bad.yaml")

    def test_non_mapping_yaml_raises_config_exception(self, tmp_path: Path) -> None:
        list_file = tmp_path / "list.yaml"
        list_file.write_text("- item1\n- item2\n", encoding="utf-8")
        loader = ConfigLoader(config_root=tmp_path)
        with pytest.raises(ConfigException):
            loader.load("list.yaml")

    def test_list_company_configs_empty_when_dir_missing(self, tmp_path: Path) -> None:
        loader = ConfigLoader(config_root=tmp_path)
        assert loader.list_company_configs() == []
