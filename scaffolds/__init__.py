"""
Skill pack scaffolding — generates Claude Code skill packs.

A skill pack is a self-contained directory with:
    packs/<slug>/
        skill.json        — manifest (name, version, deps, capabilities)
        CONTEXT.md        — domain knowledge Claude Code reads
        hooks.py          — optional Python hooks for guardrails/audit
        skills/<slug>/
            SKILL.md      — Claude Code slash command definition

Usage (from CLI):
    python orchestrator.py new-skill arcgis --description "ArcGIS Pro + arcpy"
    python orchestrator.py new-skill terraform -d "Terraform IaC patterns"

The pack is installed into Claude Code by copying the skills/ subdirectory
into .claude/skills/ (done automatically via ``install-skill``).
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Optional

SCAFFOLDS_DIR = Path(__file__).parent


def _slugify(name: str) -> str:
    """Turn a skill name into a safe slug."""
    s = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    s = re.sub(r"_+", "_", s).strip("_").lower()
    return s or "my_skill"


def _class_name(slug: str) -> str:
    """Turn a slug into a PascalCase class name."""
    return "".join(part.capitalize() for part in slug.split("_"))


def _render(template_path: Path, replacements: dict) -> str:
    """Read a .tpl file and substitute {{PLACEHOLDERS}}."""
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
    """Generate a new skill pack.

    Returns a dict mapping artifact kind -> file path.
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent  # project root

    slug = _slugify(name)
    display_name = name.strip() or slug
    description = description or f"{display_name} skill pack"
    author = author or ""

    replacements = {
        "SKILL_NAME": display_name,
        "SKILL_SLUG": slug,
        "SKILL_DESCRIPTION": description,
        "SKILL_CLASS": _class_name(slug),
        "AUTHOR": author,
    }

    pack_dir = output_dir / "packs" / slug
    pack_dir.mkdir(parents=True, exist_ok=True)

    generated = {}

    # 1. Manifest
    manifest = pack_dir / "skill.json"
    manifest.write_text(
        _render(SCAFFOLDS_DIR / "skill.json.tpl", replacements),
        encoding="utf-8",
    )
    generated["manifest"] = str(manifest)

    # 2. Domain context
    context = pack_dir / "CONTEXT.md"
    context.write_text(
        _render(SCAFFOLDS_DIR / "CONTEXT.md.tpl", replacements),
        encoding="utf-8",
    )
    generated["context"] = str(context)

    # 3. Claude Code skill (SKILL.md)
    skill_dir = pack_dir / "skills" / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        _render(SCAFFOLDS_DIR / "SKILL.md.tpl", replacements),
        encoding="utf-8",
    )
    generated["skill"] = str(skill_md)

    # 4. Optional hooks module
    hooks = pack_dir / "hooks.py"
    hooks.write_text(
        _render(SCAFFOLDS_DIR / "plugin.py.tpl", replacements),
        encoding="utf-8",
    )
    generated["hooks"] = str(hooks)

    # 5. Test file
    test_file = output_dir / "tests" / f"test_{slug}.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        _render(SCAFFOLDS_DIR / "test_plugin.py.tpl", replacements),
        encoding="utf-8",
    )
    generated["test"] = str(test_file)

    return generated


def install_skill(
    pack_dir: Path,
    target_dir: Optional[Path] = None,
) -> dict:
    """Install a skill pack into .claude/skills/ for Claude Code discovery.

    Copies SKILL.md + CONTEXT.md into .claude/skills/<name>/.
    Returns a dict mapping skill name -> destination path.
    """
    if target_dir is None:
        target_dir = Path(__file__).parent.parent / ".claude" / "skills"

    target_dir.mkdir(parents=True, exist_ok=True)
    installed = {}

    skills_src = pack_dir / "skills"
    if not skills_src.is_dir():
        return installed

    for skill_subdir in skills_src.iterdir():
        if skill_subdir.is_dir() and (skill_subdir / "SKILL.md").exists():
            dest = target_dir / skill_subdir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill_subdir, dest)
            installed[skill_subdir.name] = str(dest)

    # Copy CONTEXT.md into each installed skill dir so Claude Code can @-reference it
    context_src = pack_dir / "CONTEXT.md"
    if context_src.exists():
        for dest_path in installed.values():
            shutil.copy2(context_src, Path(dest_path) / "CONTEXT.md")

    return installed


def list_packs(packs_dir: Optional[Path] = None) -> list:
    """List all available skill packs.

    Returns a list of dicts with pack metadata.
    """
    if packs_dir is None:
        packs_dir = Path(__file__).parent.parent / "packs"

    if not packs_dir.is_dir():
        return []

    packs = []
    for pack_path in sorted(packs_dir.iterdir()):
        manifest_file = pack_path / "skill.json"
        if pack_path.is_dir() and manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                manifest["_path"] = str(pack_path)
                packs.append(manifest)
            except Exception:
                pass
    return packs
