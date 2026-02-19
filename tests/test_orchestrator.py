#!/usr/bin/env python3
"""
Basic test suite for AI Orchestrator critical components.
Run with: python -m pytest tests/ -v
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from unittest.mock import MagicMock

# Ensure 'openai' is importable for tests (mocked)
sys.modules.setdefault('openai', MagicMock())

from orchestrator import classify_code, choose_root, SAVED_DIR, RUNNING_DIR
from cloud_agent.cloud_client import _parse_any_plan, _normalize_plan
from config import Config, get_config_manager, ConfigManager


class TestCodeClassification:
    """Test the code classification logic."""

    def test_classify_program_imports(self):
        """Test classification based on GUI framework imports."""
        code_with_tkinter = "import tkinter\nroot = tkinter.Tk()\nroot.mainloop()"
        assert classify_code(code_with_tkinter) == "PROGRAM"

        code_with_flask = "from flask import Flask\napp = Flask(__name__)"
        assert classify_code(code_with_flask) == "PROGRAM"

    def test_classify_program_patterns(self):
        """Test classification based on code patterns."""
        code_with_mainloop = "root.mainloop()"
        assert classify_code(code_with_mainloop) == "PROGRAM"

        code_with_argparse = "import argparse\nparser = argparse.ArgumentParser()"
        assert classify_code(code_with_argparse) == "PROGRAM"

    def test_classify_one_off(self):
        """Test classification of simple one-off scripts."""
        simple_print = "print('Hello, World!')"
        assert classify_code(simple_print) == "ONE_OFF"

        short_calculation = "result = 2 + 2\nprint(result)"
        assert classify_code(short_calculation) == "ONE_OFF"

    def test_classify_long_code(self):
        """Test classification based on code length."""
        long_code = "\n".join([f"print({i})" for i in range(150)])
        assert classify_code(long_code) == "PROGRAM"


class TestRootSelection:
    """Test the root directory selection logic."""

    def test_choose_root_save(self):
        """Test SAVE policy always goes to SAVED."""
        assert choose_root("S", True) == SAVED_DIR
        assert choose_root("S", False) == SAVED_DIR

    def test_choose_root_delete(self):
        """Test DELETE policy always goes to RUNNING."""
        assert choose_root("D", True) == RUNNING_DIR
        assert choose_root("D", False) == RUNNING_DIR

    def test_choose_root_keep(self):
        """Test KEEP policy always goes to SAVED."""
        assert choose_root("K", True) == SAVED_DIR
        assert choose_root("K", False) == SAVED_DIR

    def test_choose_root_auto(self):
        """Test AUTO policy based on program type."""
        assert choose_root("A", True) == SAVED_DIR  # Program -> SAVED
        assert choose_root("A", False) == RUNNING_DIR  # One-off -> RUNNING


class TestPlanParsing:
    """Test JSON plan parsing and normalization."""

    def test_parse_valid_json_plan(self):
        """Test parsing a valid JSON plan."""
        valid_plan = {
            "name": "test-project",
            "description": "A test project",
            "files": [
                {
                    "filename": "main.py",
                    "code": "print('Hello, World!')"
                }
            ],
            "run": "python main.py"
        }
        raw_json = json.dumps(valid_plan)
        parsed = _parse_any_plan(raw_json)
        assert parsed["name"] == "test-project"
        assert len(parsed["files"]) == 1

    def test_parse_malformed_json(self):
        """Test parsing malformed JSON falls back gracefully."""
        malformed_json = '{"name": "test", "files": ['  # Missing closing brackets
        parsed = _parse_any_plan(malformed_json)
        # Should still return a normalized plan structure
        assert isinstance(parsed, dict)
        assert "name" in parsed or "files" in parsed

    def test_normalize_plan(self):
        """Test plan normalization."""
        minimal_plan = {"name": "test"}
        normalized = _normalize_plan(minimal_plan)
        assert normalized["name"] == "test"
        assert normalized["files"] == []
        assert normalized["description"] == ""
        assert normalized["run"] == ""


class TestConfiguration:
    """Test configuration management."""

    def test_config_loading(self):
        """Test loading configuration."""
        config_manager = get_config_manager()
        config = config_manager.config
        assert isinstance(config, Config)
        assert hasattr(config, 'llm')
        assert hasattr(config, 'behavior')
        assert hasattr(config, 'paths')
        assert hasattr(config, 'security')

    def test_config_defaults(self):
        """Test configuration defaults."""
        config = Config.from_dict({})
        assert config.llm.model == "gpt-5"
        assert config.llm.temperature == 1.0
        assert config.behavior.default_save_policy == "A"
        assert config.behavior.auto_run == True

    def test_config_file_loading(self, tmp_path):
        """Test loading configuration from file."""
        cfg = tmp_path / "config.json"
        cfg.write_text('{"llm": {"model": "gpt-4"}, "behavior": {"auto_run": false}}', encoding="utf-8")
        manager = ConfigManager(config_file=cfg)
        config = manager._load_config()

        assert config.llm.model == "gpt-4"
        assert config.behavior.auto_run == False
        # Should keep defaults for unspecified values
        assert config.llm.temperature == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])