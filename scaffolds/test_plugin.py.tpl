"""
Tests for {{SKILL_NAME}} skill pack.
Run with: python -m pytest tests/test_{{SKILL_SLUG}}.py -v
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.modules.setdefault("openai", MagicMock())

from plugins import PluginManager

PACK_DIR = Path(__file__).parent.parent / "packs" / "{{SKILL_SLUG}}"


class Test{{SKILL_CLASS}}Pack:
    """Test the {{SKILL_NAME}} skill pack structure."""

    def test_manifest_exists_and_valid(self):
        manifest_path = PACK_DIR / "skill.json"
        assert manifest_path.exists(), "skill.json manifest is missing"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["name"] == "{{SKILL_NAME}}"
        assert "description" in manifest
        assert "version" in manifest

    def test_context_file_exists(self):
        assert (PACK_DIR / "CONTEXT.md").exists(), "CONTEXT.md is missing"

    def test_skill_md_exists(self):
        skill_dir = PACK_DIR / "skills" / "{{SKILL_SLUG}}"
        assert (skill_dir / "SKILL.md").exists(), "SKILL.md is missing"

    def test_hooks_load_without_error(self):
        hooks_path = PACK_DIR / "hooks.py"
        if not hooks_path.exists():
            pytest.skip("No hooks.py — pack is context-only")
        pm = PluginManager()
        import importlib.util
        spec = importlib.util.spec_from_file_location("hooks", hooks_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "register"):
            mod.register(pm)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
