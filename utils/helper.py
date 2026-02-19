# /home/jono/ai_orchestrator/utils/helper.py
from __future__ import annotations
import os, re, stat, shlex
from pathlib import Path
from typing import Union, List, Tuple

# ---------------- Basic helpers ----------------
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

def which(cmd: str) -> bool:
    from shutil import which as _w
    return _w(cmd) is not None

# ---------------- Entry-point detection ----------------
def _detect_main(files_written: List[str]) -> Tuple[str, str]:
    """
    files_written: list of absolute file paths the orchestrator just saved.
    Returns (main_cmd_linux_mac, main_cmd_windows) strings for launchers.
    Heuristics: prefer a file with if __name__ == "__main__", else single .py,
    else first .py, else package -m if a folder has __init__.py.
    """
    py_files = [p for p in files_written if p.endswith(".py")]

    # 1) explicit __main__
    for p in py_files:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']\s*:', f.read()):
                    rel = os.path.basename(p)
                    return f"python3 {rel}", f"python {rel}"
        except Exception:
            pass

    # 2) single .py
    if len(py_files) == 1:
        rel = os.path.basename(py_files[0])
        return f"python3 {rel}", f"python {rel}"

    # 3) first .py
    if py_files:
        rel = os.path.basename(py_files[0])
        return f"python3 {rel}", f"python {rel}"

    # 4) package -m (directory containing __init__.py)
    dirs = {os.path.dirname(p) for p in files_written}
    for d in dirs:
        if os.path.isfile(os.path.join(d, "__init__.py")):
            pkg = os.path.basename(d)
            return f"python3 -m {pkg}", f"python -m {pkg}"

    # 5) last resort
    return "echo 'No entry point detected'", "echo No entry point detected"

def _write(path: Union[str, Path], text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

# ---------------- Command absolutizer ----------------
def _absolutize_main_cmd(project_dir: str, main_cmd: str) -> str:
    """
    Convert a relative main_cmd like:
      - "python3 foo.py"
      - "python -m mypkg"
      - "node app.js"
      - "bash start.sh"
    into a variant where any *file path* arg is absolute. Interpreter stays as-is.
    For -m/-c runs there's nothing reliable to absolutize, so we return unchanged.
    """
    if not main_cmd:
        return main_cmd
    parts = shlex.split(main_cmd)
    if not parts:
        return main_cmd

    # Find first file-like arg and absolutize
    for i in range(1, len(parts)):  # skip interpreter at index 0
        tok = parts[i]
        if tok in {"-m", "-c"}:
            return main_cmd
        if tok.startswith("-"):
            continue
        # treat as file if it has a path sep or extension
        if "/" in tok or "\\" in tok or Path(tok).suffix:
            abs_path = str(Path(project_dir, tok).resolve())
            parts[i] = abs_path
            break

    return " ".join(shlex.quote(p) for p in parts)

# ---------------- Launcher writer ----------------
def attach_launchers(
    project_dir: Union[str, Path],
    files_written: List[str],
    *,
    direct_cmd: str | None = None,
    is_app: bool = True,
) -> List[str]:
    """
    Ensure run.sh, run.command, run.bat exist next to the program.
    Write HOW_TO_RUN.txt ONLY if is_app=True.
    If direct_cmd is provided (e.g., final venv/poetry-aware command), prefer it.
    Otherwise derive from the written files via _detect_main().
    """
    project_dir = str(project_dir)
    main_cmd_rel, win_cmd_rel = _detect_main(files_written)

    # Prefer caller-provided command (already resolved to venv etc)
    effective_main_cmd = direct_cmd.strip() if direct_cmd else main_cmd_rel
    effective_win_cmd  = win_cmd_rel

    # Absolute command pointing at the actual script path when applicable
    main_cmd_abs = _absolutize_main_cmd(project_dir, effective_main_cmd)

    run_sh = os.path.join(project_dir, "run.sh")
    run_cmd = os.path.join(project_dir, "run.command")
    run_bat = os.path.join(project_dir, "run.bat")
    howto  = os.path.join(project_dir, "HOW_TO_RUN.txt")

    if not os.path.isfile(run_sh):
        _write(run_sh, f"""#!/usr/bin/env bash
cd "$(dirname "$0")"
{effective_main_cmd}
""")
        ensure_executable(run_sh)

    if not os.path.isfile(run_cmd):
        _write(run_cmd, f"""#!/usr/bin/env bash
cd "$(dirname "$0")"
{effective_main_cmd}
""")
        ensure_executable(run_cmd)

    if not os.path.isfile(run_bat):
        _write(run_bat, f"""@echo off
cd /d %~dp0
{effective_win_cmd}
""")

    # Only create HOW_TO_RUN for apps
    if is_app and not os.path.isfile(howto):
        abs_proj = os.path.abspath(project_dir)
        run_sh_abs  = os.path.join(abs_proj, "run.sh")
        run_cmd_abs = os.path.join(abs_proj, "run.command")
        run_bat_abs = os.path.join(abs_proj, "run.bat")

        _write(howto, f"""# How to Run (App)

## Direct app launch (absolute)
{main_cmd_abs}

## Direct app launch (relative; first cd into the folder)
{effective_main_cmd}

## Via launchers
Linux (absolute):  {run_sh_abs}
macOS (absolute):  {run_cmd_abs}
Windows (absolute): {run_bat_abs}

Linux (relative):   ./run.sh
macOS (relative):   ./run.command
Windows (relative): run.bat
""")

    return [run_sh, run_cmd, run_bat, howto]

