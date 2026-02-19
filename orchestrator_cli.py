#!/usr/bin/env python3
"""
Interactive command wrapper for AI Orchestrator.

Non-destructive: keeps tests passing by relying on the stable symbols
from orchestrator, while providing a simple command loop users can run.

Supported commands:
- /help                 Show help
- /history              List recent projects
- /open N               Open project N in file manager
- /run N                Run project N via ./run.sh
- /quit                 Exit

This is intentionally minimal but functional.
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

from orchestrator import SAVED_DIR, RUNNING_DIR, BASE_DIR
from utils.backup import create_backup
from utils.ui_dashboard import run_dashboard
from utils.runner import spawn_cmd


def _gather_projects(limit: int = 100) -> List[Path]:
    roots = [SAVED_DIR, RUNNING_DIR]
    projects: List[Tuple[float, Path]] = []
    for root in roots:
        try:
            for p in root.iterdir():
                if p.is_dir():
                    try:
                        mt = p.stat().st_mtime
                    except Exception:
                        mt = 0.0
                    projects.append((mt, p))
        except Exception:
            pass
    projects.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in projects[:limit]]


def _print_history(projects: List[Path]) -> None:
    if not projects:
        print("No projects found in SAVED/ or RUNNING/.")
        return
    print("Recent projects:")
    for i, p in enumerate(projects, 1):
        print(f"  {i:2d}. {p}")


def _open_path(p: Path) -> None:
    try:
        if sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", str(p)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        elif os.name == "nt":
            subprocess.Popen(["explorer", str(p)])
    except Exception as e:
        print(f"Open failed: {e}")


def _run_project(p: Path) -> None:
    runner = p / "run.sh"
    if not runner.exists():
        print("No run.sh in project.")
        return
    try:
        print(f"▶ Running {runner}…")
        subprocess.Popen(["bash", str(runner)], cwd=str(p))
    except Exception as e:
        print(f"Run failed: {e}")


def print_help() -> None:
    print(r"""
 █████╗ ██╗
██╔══██╗██║
███████║██║
██╔══██║██║
██║  ██║██║
╚═╝  ╚═╝╚═╝

 ██████╗ ██████╗  ██████╗ ██╗  ██╗ ███████╗ ███████╗████████╗██████╗  █████╗ ████████╗███████╗
██╔═══██╗██╔══██╗██╔════╝ ██║  ██║ ██╔════╝ ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
██║   ██║██████╔╝██║      ███████║ █████╗   ███████╗   ██║   ██████╔╝███████║   ██║   █████╗  
██║   ██║██╔══██╗██║      ██╔══██║ ██╔══╝   ╚════██║   ██║   ██╔══██╗██╔══██║   ██║   ██╔══╝  
╚██████╔╝██║  ██║╚██████╗ ██║  ██║ ███████╗ ███████║   ██║   ██║  ██║██║  ██║   ██║   ███████╗
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚══════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

AI ORCHESTRATE — AI-powered full system controller
""")
    print("Commands:")
    print("  /help            Show this help")
    print("  /history         List recent projects")
    print("  /open N          Open project N in file manager")
    print("  /run N           Run project N via ./run.sh")
    print("  /backup          Create a backup snapshot now")
    print("  /install-nightly-backup [HH:MM]  Install daily backup cron (default 02:30)")
    print("  /uninstall-nightly-backup        Remove daily backup cron entry")
    print("  /dashboard       Open the log dashboard (terminal UI)")
    print("  /gui             Launch the PySide6 desktop shell")
    print("  /web QUERY|URL   Open web browser to URL or search")
    print("  /webiso QUERY|URL   Open isolated browser (Flatpak or firejail)")
    print("  /quit            Exit")


def main() -> None:
    print("AI Orchestrator CLI — type /help for commands.\n")
    cached: List[Path] = _gather_projects()
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            print()
            break
        if not line:
            continue
        if line in ("/quit", "/exit"):
            break
        if line == "/help":
            print_help()
            continue
        if line == "/history":
            cached = _gather_projects()
            _print_history(cached)
            continue
        if line == "/backup":
            try:
                snap = create_backup(retain=14)
                print(f"Backup created: {snap}")
            except Exception as e:
                print(f"Backup failed: {e}")
            continue
        if line == "/dashboard":
            try:
                run_dashboard(BASE_DIR)
            except Exception as e:
                print(f"Dashboard error: {e}")
            continue
        if line == "/gui":
            try:
                spawn_cmd([sys.executable, str(BASE_DIR / 'gui_shell.py')])
                print("Launched GUI shell.")
            except Exception as e:
                print(f"GUI launch error: {e}")
            continue
        if line.startswith("/webiso"):
            parts = line.split(None, 1)
            if len(parts) > 1:
                os.system(f"xdg-open '{parts[1]}' >/dev/null 2>&1 &")  # fallback to open; isolated handled in main orchestrator
            else:
                print("Usage: /webiso QUERY|URL")
            continue
        if line.startswith("/web"):
            parts = line.split(None, 1)
            if len(parts) > 1:
                os.system(f"xdg-open '{parts[1]}' >/dev/null 2>&1 &")
            else:
                print("Usage: /web QUERY|URL")
            continue
        if line.startswith("/install-nightly-backup"):
            try:
                parts = line.split()
                when = parts[1] if len(parts) > 1 else "02:30"
                hh, mm = when.split(":", 1)
                hh_i = max(0, min(23, int(hh)))
                mm_i = max(0, min(59, int(mm)))
                cron_line = f"{mm_i} {hh_i} * * * {sys.executable} {BASE_DIR / 'scripts' / 'backup_now.py'} >/dev/null 2>&1"
                # Fetch existing crontab (may fail if none)
                try:
                    existing = subprocess.check_output(["crontab", "-l"], text=True)
                except Exception:
                    existing = ""
                # Remove any previous installs of our backup line
                filtered = []
                for ln in existing.splitlines():
                    if "scripts/backup_now.py" in ln:
                        continue
                    filtered.append(ln)
                new_tab = "\n".join([*(l for l in filtered if l.strip()), cron_line]) + "\n"
                p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
                p.communicate(new_tab)
                if p.returncode == 0:
                    print(f"Installed nightly backup at {hh_i:02d}:{mm_i:02d}.")
                else:
                    print("Failed to install crontab entry.")
            except Exception as e:
                print(f"Install failed: {e}")
            continue
        if line == "/uninstall-nightly-backup":
            try:
                try:
                    existing = subprocess.check_output(["crontab", "-l"], text=True)
                except Exception:
                    existing = ""
                filtered = [ln for ln in existing.splitlines() if "scripts/backup_now.py" not in ln]
                new_tab = "\n".join([l for l in filtered if l.strip()]) + ("\n" if filtered else "")
                p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
                p.communicate(new_tab)
                if p.returncode == 0:
                    print("Removed nightly backup entry.")
                else:
                    print("Failed to update crontab.")
            except Exception as e:
                print(f"Uninstall failed: {e}")
            continue
        if line.startswith("/open "):
            try:
                idx = int(line.split()[1]) - 1
                if 0 <= idx < len(cached):
                    _open_path(cached[idx])
                else:
                    print("Invalid index")
            except Exception:
                print("Usage: /open N")
            continue
        if line.startswith("/run "):
            try:
                idx = int(line.split()[1]) - 1
                if 0 <= idx < len(cached):
                    _run_project(cached[idx])
                else:
                    print("Invalid index")
            except Exception:
                print("Usage: /run N")
            continue
        print("Unknown command. Type /help.")


if __name__ == "__main__":
    main()
