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
        venv_python = VENV_DIR / "Scripts" / "python.exe"
        venv_pip = VENV_DIR / "Scripts" / "pip.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"
        venv_pip = VENV_DIR / "bin" / "pip"

    # Install deps
    req = ROOT / "requirements.txt"
    if req.exists():
        print("\nInstalling dependencies ...")
        run([str(venv_pip), "install", "-r", str(req)])

    # API key config
    print("\n=== API Key Configuration ===")
    print("The orchestrator uses an LLM for plan generation.")
    print("Set your API key via one of:")
    print(f"  1. Environment variable: export OPENAI_API_KEY='your-key'")
    print(f"  2. Local file: {ROOT / 'cloud_agent' / 'apikey.txt'}")
    print(f"  3. System keyring")
    print(f"  4. Config file: ~/.config/orchestrator-toolkit/openai_api_key")

    print(f"\nDone! Activate the venv with:")
    if os.name == "nt":
        print(f"  {VENV_DIR}\\Scripts\\activate")
    else:
        print(f"  source {VENV_DIR}/bin/activate")
    print(f"\nThen run:")
    print(f"  python orchestrator.py generate 'build a hello world API'")


if __name__ == "__main__":
    main()
