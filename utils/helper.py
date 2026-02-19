from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Union


def slugify(name: str) -> str:
    """Turn a string into a safe slug for directories."""
    s = (name or "").strip()
    s = re.sub(r"[^A-Za-z0-9_.\-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("._-") or "project"


def safe_join(base: Union[str, Path], *paths: str) -> Path:
    """Join paths safely within base directory."""
    base = Path(base).resolve()
    p = (base.joinpath(*paths)).resolve()
    if base not in p.parents and p != base:
        raise RuntimeError(f"Path escapes base dir: {p}")
    return p


def ensure_executable(path: Union[str, Path]):
    try:
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def write_run_script(project_dir: Union[str, Path], run_cmd: str) -> Path:
    """Write a simple run.sh launcher for a project."""
    project_dir = Path(project_dir)
    run_sh = project_dir / "run.sh"
    if not run_sh.exists():
        run_sh.write_text(
            f"#!/usr/bin/env bash\ncd \"$(dirname \"$0\")\"\n{run_cmd}\n",
            encoding="utf-8",
        )
        ensure_executable(run_sh)
    return run_sh
