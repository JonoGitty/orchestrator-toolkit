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
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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

    # bootstrap: set up patchwork hooks for Claude Code
    boot = sub.add_parser("bootstrap", help="Set up patchwork audit + hooks for Claude Code")
    boot.add_argument(
        "--project", "-p", type=Path, default=None,
        help="Target project directory (default: current directory)",
    )

    # audit: view the patchwork audit trail
    aud = sub.add_parser("audit", help="View the patchwork audit trail")
    aud.add_argument("--session", "-s", default=None, help="Filter by session ID")
    aud.add_argument("--tail", "-n", type=int, default=20, help="Number of entries to show")
    aud.add_argument(
        "--project", "-p", type=Path, default=None,
        help="Project directory (default: current directory)",
    )

    return p


# ---------------------------------------------------------------------------
# Bootstrap — wire patchwork into a project
# ---------------------------------------------------------------------------

_PATCHWORK_HOOKS: Dict[str, Any] = {
    "PreToolUse": [
        {
            "matcher": "",
            "hooks": [{
                "type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/plugins/patchwork.py\"",
                "timeout": 10,
            }],
        },
    ],
    "PostToolUse": [
        {
            "matcher": "",
            "hooks": [{
                "type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/plugins/patchwork.py\"",
                "timeout": 10,
                "async": True,
            }],
        },
    ],
    "SessionStart": [
        {
            "matcher": "",
            "hooks": [{
                "type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/plugins/patchwork.py\"",
                "timeout": 10,
            }],
        },
    ],
    "SessionEnd": [
        {
            "matcher": "",
            "hooks": [{
                "type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/plugins/patchwork.py\"",
                "timeout": 10,
                "async": True,
            }],
        },
    ],
}


def _cmd_bootstrap(project_dir: Path) -> int:
    """Set up patchwork audit + Claude Code hooks in a project."""
    project_dir = project_dir.resolve()
    patchwork_dir = project_dir / ".patchwork"
    claude_dir = project_dir / ".claude"
    settings_file = claude_dir / "settings.json"

    print(f"Bootstrapping patchwork in {project_dir}\n")

    # 1. Create .patchwork/ directory
    patchwork_dir.mkdir(parents=True, exist_ok=True)
    (patchwork_dir / "audit.jsonl").touch()
    print(f"  Created .patchwork/audit.jsonl")

    # 2. Copy default policies
    policies_src = BASE_DIR / "policies"
    policies_dst = patchwork_dir / "policies"
    if policies_src.is_dir() and not policies_dst.is_dir():
        shutil.copytree(policies_src, policies_dst)
        print(f"  Copied default policies to .patchwork/policies/")
    elif policies_dst.is_dir():
        print(f"  Policies already exist at .patchwork/policies/")

    # 3. Write patchwork config
    config_file = patchwork_dir / "config.yaml"
    if not config_file.exists():
        config_file.write_text(
            "# Patchwork configuration\n"
            "audit_enabled: true\n"
            "policy_enforcement: true\n"
            "log_reads: false\n",
            encoding="utf-8",
        )
        print(f"  Created .patchwork/config.yaml")

    # 4. Merge hooks into .claude/settings.json
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings: Dict[str, Any] = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
        except Exception:
            settings = {}

    existing_hooks = settings.get("hooks", {})
    for event, hook_list in _PATCHWORK_HOOKS.items():
        if event not in existing_hooks:
            existing_hooks[event] = []
        # Check if patchwork hook already installed for this event
        already = any(
            "patchwork.py" in h.get("command", "")
            for group in existing_hooks[event]
            for h in group.get("hooks", [])
        )
        if not already:
            existing_hooks[event].extend(hook_list)

    settings["hooks"] = existing_hooks
    settings_file.write_text(
        json.dumps(settings, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  Updated .claude/settings.json with patchwork hooks")

    # 5. Update .gitignore
    gitignore = project_dir / ".gitignore"
    gitignore_lines: List[str] = []
    if gitignore.exists():
        gitignore_lines = gitignore.read_text(encoding="utf-8").splitlines()

    additions = []
    for pattern in [".patchwork/audit.jsonl", ".patchwork/config.yaml"]:
        if pattern not in gitignore_lines:
            additions.append(pattern)

    if additions:
        with open(gitignore, "a", encoding="utf-8") as f:
            if gitignore_lines and gitignore_lines[-1].strip():
                f.write("\n")
            f.write("# Patchwork audit (local)\n")
            for pat in additions:
                f.write(pat + "\n")
        print(f"  Updated .gitignore")

    # 6. Update CLAUDE.md
    claude_md = claude_dir / "CLAUDE.md"
    patchwork_marker = "## Patchwork Audit"
    if claude_md.exists():
        existing = claude_md.read_text(encoding="utf-8")
        if patchwork_marker not in existing:
            with open(claude_md, "a", encoding="utf-8") as f:
                f.write("\n" + _PATCHWORK_CLAUDE_MD)
            print(f"  Updated .claude/CLAUDE.md with patchwork instructions")
        else:
            print(f"  .claude/CLAUDE.md already has patchwork section")
    else:
        claude_md.write_text(_PATCHWORK_CLAUDE_MD, encoding="utf-8")
        print(f"  Created .claude/CLAUDE.md")

    print(f"\nPatchwork is ready. Claude Code will now:")
    print(f"  - Log every tool call to .patchwork/audit.jsonl")
    print(f"  - Enforce policies from .patchwork/policies/")
    print(f"  - Inject audit context on session start")
    print(f"\nView the audit trail:")
    print(f"  python orchestrator.py audit")
    return 0


_PATCHWORK_CLAUDE_MD = """\
## Patchwork Audit

Patchwork is active in this project. Every tool call (Bash, Write, Edit, Read,
etc.) is logged to `.patchwork/audit.jsonl` and checked against security
policies in `.patchwork/policies/`.

**What this means for you:**
- If a tool call is denied by policy, explain the denial to the user and
  suggest a safe alternative. Do NOT attempt to bypass the policy.
- Dangerous operations (rm -rf /, force push, writing .env files, etc.) are
  blocked automatically.
- Some operations trigger warnings — these are allowed but logged with a note.

**Audit trail:** `.patchwork/audit.jsonl` — one JSON line per event.

**Policies:** `.patchwork/policies/default.yaml` — edit to customize rules.

**View the log:** `python orchestrator.py audit`
"""


# ---------------------------------------------------------------------------
# Audit — view the trail
# ---------------------------------------------------------------------------

def _cmd_audit(project_dir: Path, session_filter: Optional[str], tail: int) -> int:
    """Print recent audit log entries."""
    audit_file = project_dir.resolve() / ".patchwork" / "audit.jsonl"
    if not audit_file.exists():
        print("No audit log found. Run 'python orchestrator.py bootstrap' first.")
        return 1

    # Read all lines, filter, take last N
    entries: List[Dict[str, Any]] = []
    with open(audit_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if session_filter and entry.get("session", "") != session_filter:
                    continue
                entries.append(entry)
            except json.JSONDecodeError:
                continue

    if not entries:
        print("No audit entries found.")
        return 0

    # Take last N
    entries = entries[-tail:]

    # Pretty print
    for entry in entries:
        ts = entry.get("ts", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                ts = dt.strftime("%H:%M:%S")
            except ValueError:
                ts = ts[:19]

        event = entry.get("event", "?")
        tool = entry.get("tool", "")
        decision = entry.get("decision", "")
        inp = entry.get("input", "")
        session = entry.get("session", "")[:8]

        if event == "session_start":
            print(f"  {ts}  [{session}]  SESSION START  cwd={entry.get('cwd', '')}")
        elif event == "session_end":
            print(f"  {ts}  [{session}]  SESSION END")
        elif event == "pre_tool":
            marker = "DENY" if decision == "deny" else "ok"
            reason = entry.get("reason", "")
            warning = entry.get("warning", "")
            line = f"  {ts}  [{session}]  {marker:4s}  {tool:8s}  {inp}"
            if reason:
                line += f"  -- {reason}"
            if warning:
                line += f"  !! {warning}"
            print(line)
        elif event == "post_tool":
            print(f"  {ts}  [{session}]  done  {tool:8s}  {inp}")
        else:
            print(f"  {ts}  [{session}]  {event}")

    total_count = 0
    try:
        with open(audit_file, "r", encoding="utf-8") as f:
            total_count = sum(1 for _ in f)
    except OSError:
        pass

    print(f"\nShowing {len(entries)} of {total_count} entries.")
    if session_filter:
        print(f"Filtered to session: {session_filter}")
    print(f"Log: {audit_file}")
    return 0


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
    # Patchwork audit commands
    # ------------------------------------------------------------------

    elif args.command == "bootstrap":
        return _cmd_bootstrap(args.project or Path.cwd())

    elif args.command == "audit":
        return _cmd_audit(args.project or Path.cwd(), args.session, args.tail)

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        raise SystemExit(1)
