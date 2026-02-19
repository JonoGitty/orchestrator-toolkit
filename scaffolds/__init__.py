"""
Skill scaffolding — generates new plugin boilerplate from templates.

Usage (from CLI):
    python orchestrator.py new-skill my-awesome-skill
    python orchestrator.py new-skill my-awesome-skill --author "Jane Doe" --description "Does cool stuff"

This creates:
    plugins/my_awesome_skill.py   — the plugin module
    plugins/my_awesome_skill/skill.json — the manifest
    tests/test_my_awesome_skill.py — starter tests
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

SCAFFOLDS_DIR = Path(__file__).parent


def _slugify(name: str) -> str:
    """Turn a skill name into a valid Python identifier slug."""
    s = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    s = re.sub(r"_+", "_", s).strip("_").lower()
    return s or "my_skill"


def _class_name(slug: str) -> str:
    """Turn a slug into a PascalCase class name."""
    return "".join(part.capitalize() for part in slug.split("_"))


def _render(template_path: Path, replacements: dict) -> str:
    """Read a template and substitute {{PLACEHOLDERS}}."""
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def generate_skill(
    name: str,
    *,
    description: str = "",
    author: str = "",
    output_dir: Optional[Path] = None,
) -> dict:
    """Generate a new skill scaffold.

    Returns a dict with paths to all generated files.
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent  # project root

    slug = _slugify(name)
    display_name = name.strip() or slug
    description = description or f"{display_name} skill plugin"
    author = author or ""

    replacements = {
        "SKILL_NAME": display_name,
        "SKILL_SLUG": slug,
        "SKILL_DESCRIPTION": description,
        "SKILL_CLASS": _class_name(slug),
        "AUTHOR": author,
    }

    generated = {}

    # 1. Plugin module → plugins/<slug>.py
    plugin_file = output_dir / "plugins" / f"{slug}.py"
    plugin_file.parent.mkdir(parents=True, exist_ok=True)
    plugin_file.write_text(
        _render(SCAFFOLDS_DIR / "plugin.py.tpl", replacements),
        encoding="utf-8",
    )
    generated["plugin"] = str(plugin_file)

    # 2. Skill manifest → plugins/<slug>/skill.json
    manifest_dir = output_dir / "plugins" / slug
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "skill.json"
    manifest_file.write_text(
        _render(SCAFFOLDS_DIR / "skill.json.tpl", replacements),
        encoding="utf-8",
    )
    generated["manifest"] = str(manifest_file)

    # 3. Packaging template → plugins/<slug>/setup.py
    setup_file = manifest_dir / "setup.py"
    setup_file.write_text(
        _render(SCAFFOLDS_DIR / "setup.py.tpl", replacements),
        encoding="utf-8",
    )
    generated["setup"] = str(setup_file)

    # 4. Test file → tests/test_<slug>.py
    test_file = output_dir / "tests" / f"test_{slug}.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        _render(SCAFFOLDS_DIR / "test_plugin.py.tpl", replacements),
        encoding="utf-8",
    )
    generated["test"] = str(test_file)

    return generated
