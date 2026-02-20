#!/usr/bin/env python3
"""Setup script for Orchestrator Toolkit."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"


def run(cmd, **kwargs):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.check_call(cmd, **kwargs)


def main() -> None:
    print("=== Orchestrator Toolkit Setup ===\n")

    # Create venv
    if not VENV_DIR.exists():
        print(f"Creating virtualenv at {VENV_DIR} ...")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print(f"Virtualenv already exists at {VENV_DIR}")

    # Pip & python inside venv
    if os.name == "nt":
        venv_pip = VENV_DIR / "Scripts" / "pip.exe"
    else:
        venv_pip = VENV_DIR / "bin" / "pip"

    # Install deps
    req = ROOT / "requirements.txt"
    if req.exists():
        print("\nInstalling dependencies ...")
        run([str(venv_pip), "install", "-r", str(req)])

    print(f"\nDone! Activate the venv with:")
    if os.name == "nt":
        print(f"  {VENV_DIR}\\Scripts\\activate")
    else:
        print(f"  source {VENV_DIR}/bin/activate")
    print(f"\nThen run:")
    print(f"  python orchestrator.py list-packs")
    print(f"  python orchestrator.py new-skill <name>")
    print(f"  python orchestrator.py install-skill <name>")


if __name__ == "__main__":
    main()
