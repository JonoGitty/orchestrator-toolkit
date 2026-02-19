#!/usr/bin/env python3
"""
Test suite for Orchestrator Toolkit.
Run with: python -m pytest tests/ -v
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure 'openai' is importable for tests (mocked)
sys.modules.setdefault("openai", MagicMock())

from cloud_agent.cloud_client import _parse_any_plan, _normalize_plan
from config import Config, ConfigManager, get_config_manager
from plugins import PluginManager


class TestPlanParsing:
    """Test JSON plan parsing and normalization."""

    def test_parse_valid_json_plan(self):
        valid_plan = {
            "name": "test-project",
            "description": "A test project",
            "files": [{"filename": "main.py", "code": "print('Hello')"}],
            "run": "python main.py",
        }
        raw_json = json.dumps(valid_plan)
        parsed = _parse_any_plan(raw_json)
        assert parsed["name"] == "test-project"
        assert len(parsed["files"]) == 1

    def test_parse_malformed_json(self):
        malformed = '{"name": "test", "files": ['
        parsed = _parse_any_plan(malformed)
        assert isinstance(parsed, dict)
        assert "name" in parsed or "files" in parsed

    def test_normalize_plan_minimal(self):
        normalized = _normalize_plan({"name": "test"})
        assert normalized["name"] == "test"
        assert normalized["files"] == []
        assert normalized["description"] == ""
        assert normalized["run"] == ""

    def test_normalize_plan_array(self):
        files = [{"filename": "app.py", "code": "print(1)"}]
        normalized = _normalize_plan(files)
        assert len(normalized["files"]) == 1
        assert normalized["files"][0]["filename"] == "app.py"

    def test_normalize_plan_string(self):
        normalized = _normalize_plan("print('hello')")
        assert normalized["files"][0]["filename"] == "main.py"


class TestConfiguration:
    """Test configuration management."""

    def test_config_loading(self):
        config = get_config_manager().config
        assert isinstance(config, Config)
        assert hasattr(config, "llm")
        assert hasattr(config, "paths")
        assert hasattr(config, "plugins")
        assert hasattr(config, "security")

    def test_config_defaults(self):
        config = Config.from_dict({})
        assert config.llm.model == "gpt-4.1"
        assert config.llm.temperature == 1.0
        assert config.llm.max_retries == 3
        assert config.paths.output_dir == "output"
        assert config.plugins.enabled == []

    def test_config_file_loading(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(
            '{"llm": {"model": "claude-sonnet-4-5-20250929"}, "paths": {"output_dir": "out"}}',
            encoding="utf-8",
        )
        manager = ConfigManager(config_file=cfg)
        config = manager._load_config()
        assert config.llm.model == "claude-sonnet-4-5-20250929"
        assert config.paths.output_dir == "out"
        # Defaults preserved for unspecified values
        assert config.llm.temperature == 1.0

    def test_config_has_no_legacy_fields(self):
        """Ensure legacy app-builder config is gone."""
        config = Config.from_dict({})
        assert not hasattr(config, "behavior")
        assert not hasattr(config, "shortcuts")
        d = config.to_dict()
        assert "behavior" not in d
        assert "shortcuts" not in d


class TestPluginManager:
    """Test the plugin system."""

    def test_add_and_fire_hook(self):
        pm = PluginManager()
        results = []
        pm.add_hook("pre_execute", lambda plan, **kw: results.append(plan))
        pm.hook("pre_execute", plan={"name": "test"})
        assert len(results) == 1
        assert results[0]["name"] == "test"

    def test_hook_returns_last_value(self):
        pm = PluginManager()
        pm.add_hook("pre_execute", lambda plan, **kw: {**plan, "modified": True})
        result = pm.hook("pre_execute", plan={"name": "test"})
        assert result["modified"] is True

    def test_invalid_hook_name_raises(self):
        pm = PluginManager()
        with pytest.raises(ValueError):
            pm.add_hook("invalid_event", lambda: None)

    def test_register_and_list(self):
        pm = PluginManager()
        pm.register_plugin("test-plugin", "A test plugin")
        plugins = pm.list_plugins()
        assert len(plugins) == 1
        assert plugins[0] == ("test-plugin", "A test plugin")

    def test_hook_error_does_not_crash(self):
        pm = PluginManager()
        pm.add_hook("pre_execute", lambda plan, **kw: 1 / 0)  # raises
        pm.add_hook("pre_execute", lambda plan, **kw: plan)
        result = pm.hook("pre_execute", plan={"name": "test"})
        assert result["name"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
