#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Callable

# Discover repo base from this file
BASE_DIR = Path(__file__).resolve().parents[1]
BACKUP_DIR = BASE_DIR / "BACKUP"


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _default_includes() -> list[Path]:
    # Key code directories to snapshot
    dirs = [
        "cloud_agent",
        "local_agent",
        "runtime",
        "tests",
        "utils",
        "docs",
        "scripts",
    ]
    out: list[Path] = []
    for d in dirs:
        p = BASE_DIR / d
        if p.exists() and p.is_dir():
            out.append(p)
    return out


def _default_root_files() -> list[Path]:
    patterns = [
        "*.py",
        "pyproject.toml",
        "requirements*.txt",
        "README.md",
        "setup.py",
        "pytest.ini",
        "*.txt",
    ]
    files: list[Path] = []
    for pat in patterns:
        files.extend(BASE_DIR.glob(pat))
    # Filter out top-level dirs and compiled/cache items
    files = [f for f in files if f.is_file() and f.parent == BASE_DIR]
    return files


def _dir_ignore() -> Callable[[str, list[str]], set[str]]:
    skip_names = {"__pycache__", ".pytest_cache", ".mypy_cache", ".cache", ".git", ".idea", ".vscode",
                  ".venv", "venv", "env", "node_modules", "dist", "build"}

    def ignore(dirpath: str, names: list[str]) -> set[str]:
        base = Path(dirpath)
        ignored: set[str] = set()
        for n in names:
            # Skip heavy roots or temp artefacts
            if n in skip_names:
                ignored.add(n); continue
            # Never recurse into RUNNING or SAVED from any included dir
            if n in {"RUNNING", "SAVED", "BACKUP", "SAVED.bak", "RUNNING.bak"}:
                ignored.add(n); continue
            # Skip large virtual env folders anywhere
            if n.endswith(".venv") or n.endswith(".env"):
                ignored.add(n); continue
        return ignored

    return ignore


def create_backup(retain: int | None = None) -> Path:
    """
    Create a timestamped snapshot of key project code into BACKUP/<stamp>/.

    Returns the snapshot directory path. If retain is provided, keep only
    the newest N snapshots and purge older ones.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()
    snap_dir = BACKUP_DIR / stamp
    snap_dir.mkdir(parents=True, exist_ok=False)

    # Copy selected top-level files
    for f in _default_root_files():
        try:
            shutil.copy2(str(f), str(snap_dir / f.name))
        except Exception as e:
            print(f"[backup] warn: failed to copy file {f}: {e}", file=sys.stderr)

    # Copy selected directories with ignore rules
    ignore = _dir_ignore()
    for d in _default_includes():
        try:
            shutil.copytree(str(d), str(snap_dir / d.name), dirs_exist_ok=False, ignore=ignore)
        except Exception as e:
            print(f"[backup] warn: failed to copy dir {d}: {e}", file=sys.stderr)

    # Best-effort: also copy minimal orchestrator entrypoint if not caught by *.py
    for name in ["orchestrator.py", "orchestrator_cli.py", "config.py"]:
        src = BASE_DIR / name
        if src.exists() and src.is_file():
            try:
                shutil.copy2(str(src), str(snap_dir / name))
            except Exception as e:
                print(f"[backup] warn: failed to copy {name}: {e}", file=sys.stderr)

    # Optional retention pruning
    if isinstance(retain, int) and retain > 0:
        prune_old_snapshots(BACKUP_DIR, retain)

    return snap_dir


def prune_old_snapshots(root: Path | None = None, keep: int = 14) -> None:
    root = root or BACKUP_DIR
    if not root.exists():
        return
    snaps = [p for p in root.iterdir() if p.is_dir()]
    snaps.sort(key=lambda p: p.name, reverse=True)
    for stale in snaps[keep:]:
        try:
            shutil.rmtree(stale)
        except Exception as e:
            print(f"[backup] warn: failed to remove old snapshot {stale}: {e}", file=sys.stderr)


if __name__ == "__main__":
    keep_n = None
    try:
        keep_env = os.environ.get("BACKUP_RETAIN")
        if keep_env:
            keep_n = int(keep_env)
    except Exception:
        keep_n = None
    p = create_backup(retain=keep_n)
    print(str(p))
