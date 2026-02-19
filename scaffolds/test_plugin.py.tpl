"""
Tests for {{SKILL_NAME}} skill plugin.
Run with: python -m pytest tests/test_{{SKILL_SLUG}}.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.modules.setdefault("openai", MagicMock())

from plugins import PluginManager


class Test{{SKILL_CLASS}}:
    """Test the {{SKILL_NAME}} plugin."""

    def _make_manager(self):
        pm = PluginManager()
        # Import and register the plugin
        import plugins.{{SKILL_SLUG}} as skill
        skill.register(pm)
        return pm

    def test_registers_hooks(self):
        pm = self._make_manager()
        # Verify hooks were registered
        assert len(pm._hooks["pre_execute"]) >= 1
        assert len(pm._hooks["post_execute"]) >= 1

    def test_pre_execute_passes_plan(self):
        pm = self._make_manager()
        plan = {"name": "test-project", "files": []}
        result = pm.hook("pre_execute", plan=plan)
        # Should return None (pass-through) or the plan
        assert result is None or isinstance(result, dict)

    def test_post_execute_runs(self):
        pm = self._make_manager()
        plan = {"name": "test-project", "files": []}
        result_data = {"project_dir": "/tmp/test", "stack": "python"}
        # Should not raise
        pm.hook("post_execute", plan=plan, result=result_data)

    def test_plugin_metadata(self):
        import plugins.{{SKILL_SLUG}} as skill
        assert hasattr(skill, "PLUGIN_NAME")
        assert hasattr(skill, "PLUGIN_DESCRIPTION")
        assert hasattr(skill, "PLUGIN_VERSION")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
