#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

# Resolve project base and log file
BASE_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = BASE_DIR / "runtime"
LOG_FILE = RUNTIME_DIR / "command_log.jsonl"

RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

MAX_CAPTURE = 8192  # chars per stream to keep in log


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_list(cmd: Sequence[str] | str) -> list[str]:
    if isinstance(cmd, str):
        return ["/bin/sh", "-c", cmd]
    return list(cmd)


def _prompt_confirm(cmd_str: str) -> bool:
    if not sys.stdin.isatty():
        # Non-interactive: default deny for safety
        return False
    try:
        ans = input(f"Allow command?\n  {cmd_str}\n[y/N]: ").strip().lower()
    except EOFError:
        ans = ""
    return ans in {"y", "yes"}


def _truncate(s: str | bytes | None, limit: int = MAX_CAPTURE) -> str:
    if s is None:
        return ""
    if isinstance(s, bytes):
        try:
            s = s.decode("utf-8", errors="replace")
        except Exception:
            s = s.decode(errors="replace")
    s = str(s)
    if len(s) <= limit:
        return s
    return s[:limit] + f"\n… [truncated {len(s) - limit} chars]"


def _write_log(entry: dict[str, Any]) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Best-effort logging; never raise
        pass


def run_cmd(
    cmd: Sequence[str] | str,
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    mode: str = "read",  # "read" safe auto-run, "write" prompts
    confirm: bool | None = None,
    timeout: float | None = None,
    shell: bool = False,
) -> dict[str, Any]:
    """
    Execute a command, capture stdout/stderr, log JSONL, and return a result dict:
    { 'rc': int, 'stdout': str, 'stderr': str, 'cmd': [...], 'cwd': str }
    """
    argv = _ensure_list(cmd) if not shell else ["/bin/sh", "-c", str(cmd)]
    cmd_str = " ".join(shlex.quote(x) for x in (cmd if isinstance(cmd, (list, tuple)) else [cmd]))

    # Determine if we need user confirmation
    need_confirm = (mode == "write") if confirm is None else bool(confirm)
    if need_confirm:
        allowed = _prompt_confirm(cmd_str)
        if not allowed:
            entry = {
                "ts": _now_iso(),
                "cmd": argv,
                "cwd": str(cwd or os.getcwd()),
                "env_keys": sorted(list((env or {}).keys())),
                "mode": mode,
                "rc": None,
                "denied": True,
            }
            _write_log(entry)
            return {"rc": 126, "stdout": "", "stderr": "Denied by user", "cmd": argv, "cwd": str(cwd or os.getcwd())}

    try:
        p = subprocess.Popen(
            argv,
            cwd=str(cwd) if cwd else None,
            env={**os.environ, **(env or {})},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
            rc = 124
        else:
            rc = p.returncode
    except FileNotFoundError as e:
        out, err, rc = "", str(e), 127
    except Exception as e:
        out, err, rc = "", str(e), 1

    entry = {
        "ts": _now_iso(),
        "cmd": argv,
        "cwd": str(cwd or os.getcwd()),
        "env_keys": sorted(list((env or {}).keys())),
        "mode": mode,
        "rc": rc,
        "stdout": _truncate(out),
        "stderr": _truncate(err),
    }
    _write_log(entry)

    return {"rc": rc, "stdout": out or "", "stderr": err or "", "cmd": argv, "cwd": str(cwd or os.getcwd())}


def spawn_cmd(
    cmd: Sequence[str] | str,
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    """Spawn a detached process (no capture); still logs the intent."""
    argv = _ensure_list(cmd)
    rc = 0
    try:
        subprocess.Popen(
            argv,
            cwd=str(cwd) if cwd else None,
            env={**os.environ, **(env or {})},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        rc = 0
    except FileNotFoundError as e:
        rc = 127
    except Exception:
        rc = 1
    entry = {
        "ts": _now_iso(),
        "cmd": argv,
        "cwd": str(cwd or os.getcwd()),
        "env_keys": sorted(list((env or {}).keys())),
        "mode": "spawn",
        "rc": rc,
    }
    _write_log(entry)
    return rc
