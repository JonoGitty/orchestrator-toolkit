#!/usr/bin/env python3
"""
Orchestrator Toolkit — skill pack manager for AI coding agents.

Manages domain knowledge packs (skills) that teach Claude Code, OpenClaw,
and other AI agents about specific domains (ArcGIS, Terraform, etc.).
Also provides plan execution, multi-stack building, and plugin hooks.
Patchwork (codex-audit) integration tracks everything.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from cloud_agent.cloud_client import get_plan
from config import get_config
from plugins import PluginManager
from runtime.plan_runner import apply_plan, set_plugin_manager
from utils.runner import run_cmd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")

# Project root
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
PACKS_DIR = BASE_DIR / "packs"


# ---------------------------------------------------------------------------
# Core orchestration API
# ---------------------------------------------------------------------------

def generate_plan(prompt: str, **kwargs) -> Dict[str, Any]:
    """Generate an execution plan from a natural-language prompt via LLM."""
    logger.info("Generating plan for prompt: %s", prompt[:120])
    plan = get_plan(prompt, **kwargs)
    logger.info("Plan generated: %s (%d files)", plan.get("name", "?"), len(plan.get("files", [])))
    return plan


def execute_plan(
    plan: Dict[str, Any],
    output_dir: Optional[Path] = None,
    plugins: Optional[PluginManager] = None,
) -> Dict[str, Any]:
    """
    Execute a plan: write files, detect stack, install deps, build.

    If a PluginManager is provided, lifecycle hooks fire at each stage:
      - pre_execute(plan)
      - post_execute(plan, result)
    """
    output_dir = output_dir or OUTPUT_DIR

    if plugins:
        plan = plugins.hook("pre_execute", plan=plan) or plan
        set_plugin_manager(plugins)

    result = apply_plan(plan, output_dir)

    # Clear the module-level reference
    set_plugin_manager(None)
    logger.info("Plan applied -> %s (stack=%s)", result.get("project_dir"), result.get("stack"))

    if plugins:
        plugins.hook("post_execute", plan=plan, result=result)

    return result


def run_project(project_dir: Path, plugins: Optional[PluginManager] = None) -> int:
    """Run a project via its run.sh launcher (if present)."""
    runner = project_dir / "run.sh"
    if not runner.exists():
        logger.warning("No run.sh in %s", project_dir)
        return 1
    logger.info("Running project: %s", project_dir)

    if plugins:
        plugins.hook("pre_run", project_dir=project_dir)

    res = run_cmd(["bash", str(runner)], cwd=str(project_dir), mode="read")
    rc = res.get("rc", 1)
    if res.get("stdout"):
        print(res["stdout"])
    if res.get("stderr"):
        print(res["stderr"], file=sys.stderr)

    if plugins:
        plugins.hook("post_run", project_dir=project_dir, rc=rc)

    return rc


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="orchestrator",
        description="Orchestrator Toolkit — skill pack manager for AI coding agents",
    )
    sub = p.add_subparsers(dest="command")

    # --- Skill pack management ---

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

    # --- Plan execution (legacy / CI) ---

    # generate: prompt -> plan -> build
    gen = sub.add_parser("generate", help="Generate and build a project from a prompt")
    gen.add_argument("prompt", nargs="+", help="Natural-language prompt")
    gen.add_argument("-o", "--output", type=Path, default=None, help="Output directory")

    # execute: plan.json -> build
    exe = sub.add_parser("execute", help="Execute an existing plan JSON file")
    exe.add_argument("plan_file", type=Path, help="Path to plan JSON")
    exe.add_argument("-o", "--output", type=Path, default=None, help="Output directory")

    # run: run an already-built project
    run = sub.add_parser("run", help="Run an already-built project")
    run.add_argument("project_dir", type=Path, help="Project directory")

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

    # ------------------------------------------------------------------
    # Plan execution commands (for CI / headless use)
    # ------------------------------------------------------------------

    elif args.command == "generate":
        prompt = " ".join(args.prompt)
        plan = generate_plan(prompt)
        result = execute_plan(plan, output_dir=args.output, plugins=plugins)
        print(f"\nProject ready: {result['project_dir']}")
        print(f"Stack: {result.get('stack', 'unknown')}")
        if result.get("run_cmd"):
            print(f"Run:   {result['run_cmd']}")
        return 0

    elif args.command == "execute":
        plan = json.loads(args.plan_file.read_text(encoding="utf-8"))
        result = execute_plan(plan, output_dir=args.output, plugins=plugins)
        print(f"\nProject ready: {result['project_dir']}")
        return 0

    elif args.command == "run":
        return run_project(args.project_dir, plugins=plugins)

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        raise SystemExit(1)
