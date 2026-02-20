#!/usr/bin/env python3
"""
Orchestrator Toolkit — skill pack manager for AI coding agents.

Manages domain knowledge packs (skills) that teach Claude Code, OpenClaw,
and other AI agents about specific domains (ArcGIS, Terraform, etc.).
Plugin system provides lifecycle hooks for extensibility.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from plugins import PluginManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")

# Project root
BASE_DIR = Path(__file__).resolve().parent
PACKS_DIR = BASE_DIR / "packs"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="orchestrator",
        description="Orchestrator Toolkit — skill pack manager for AI coding agents",
    )
    sub = p.add_subparsers(dest="command")

    # new-skill: scaffold a new skill pack
    ns = sub.add_parser("new-skill", help="Create a new skill pack")
    ns.add_argument("name", help="Skill name (e.g. 'arcgis', 'terraform')")
    ns.add_argument("--description", "-d", default="", help="Short description")
    ns.add_argument("--author", "-a", default="", help="Author name")

    # install-skill: install a pack into .claude/skills/
    inst = sub.add_parser("install-skill", help="Install a skill pack into Claude Code")
    inst.add_argument("pack", help="Pack name (from packs/) or path to pack directory")

    # list-packs: show available skill packs
    sub.add_parser("list-packs", help="List available skill packs")

    # plugins: list loaded hook plugins
    sub.add_parser("plugins", help="List loaded hook plugins")

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    plugins = PluginManager()
    plugins.discover()

    # ------------------------------------------------------------------
    # Skill pack management commands
    # ------------------------------------------------------------------

    if args.command == "new-skill":
        from scaffolds import generate_skill
        generated = generate_skill(
            args.name,
            description=args.description,
            author=args.author,
            output_dir=BASE_DIR,
        )
        print(f"Skill pack '{args.name}' created!")
        print()
        for kind, path in generated.items():
            print(f"  {kind:10s} -> {path}")
        print()
        print("Next steps:")
        print(f"  1. Fill in packs/...CONTEXT.md with domain knowledge")
        print(f"  2. Edit the SKILL.md slash command definition")
        print(f"  3. Install into Claude Code: python orchestrator.py install-skill {args.name}")
        return 0

    elif args.command == "install-skill":
        from scaffolds import install_skill
        # Resolve pack path: either a name in packs/ or a direct path
        pack_path = Path(args.pack)
        if not pack_path.is_dir():
            pack_path = PACKS_DIR / args.pack
        if not pack_path.is_dir():
            print(f"Pack not found: {args.pack}")
            print(f"Available packs: {', '.join(p.name for p in PACKS_DIR.iterdir() if p.is_dir())}"
                  if PACKS_DIR.is_dir() else "No packs/ directory found.")
            return 1

        installed = install_skill(pack_path, target_dir=BASE_DIR / ".claude" / "skills")
        if installed:
            print(f"Installed skill pack from {pack_path.name}:")
            for name, dest in installed.items():
                print(f"  /{name} -> {dest}")
            print(f"\nClaude Code will now see the /{list(installed.keys())[0]} command.")
        else:
            print(f"No SKILL.md files found in {pack_path}")
        return 0

    elif args.command == "list-packs":
        from scaffolds import list_packs
        packs = list_packs(PACKS_DIR)
        if not packs:
            print("No skill packs found in packs/")
            print("Create one: python orchestrator.py new-skill <name>")
        else:
            print(f"Available skill packs ({len(packs)}):\n")
            for p in packs:
                line = f"  {p['name']}"
                if p.get("version") and p["version"] != "0.0.0":
                    line += f" v{p['version']}"
                if p.get("description"):
                    line += f" — {p['description']}"
                print(line)
                if p.get("capabilities"):
                    print(f"    capabilities: {', '.join(p['capabilities'])}")
            print(f"\nInstall: python orchestrator.py install-skill <name>")
        return 0

    elif args.command == "plugins":
        loaded = plugins.list_plugins_detailed()
        if not loaded:
            print("No hook plugins loaded.")
        else:
            print("Loaded hook plugins:")
            for p in loaded:
                line = f"  - {p['name']}"
                if p.get("version") and p["version"] != "0.0.0":
                    line += f" v{p['version']}"
                if p.get("description"):
                    line += f": {p['description']}"
                print(line)
                if p.get("dependencies"):
                    print(f"    deps: {', '.join(p['dependencies'])}")
                if p.get("capabilities"):
                    print(f"    caps: {', '.join(p['capabilities'])}")
        # Show registered hooks
        hook_names = plugins.get_hook_names()
        custom = [h for h in hook_names if h not in (
            "pre_execute", "post_execute", "pre_run", "post_run",
            "detect_stack", "pre_build", "post_build",
        )]
        if custom:
            print(f"\nCustom hook events: {', '.join(custom)}")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        raise SystemExit(1)
