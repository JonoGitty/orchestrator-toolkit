#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

# Allow running without package install
import sys
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from utils.backup import create_backup


def main() -> None:
    retain = int(os.environ.get("BACKUP_RETAIN", "14"))
    snap = create_backup(retain)
    print(f"Backup created: {snap}")


if __name__ == "__main__":
    main()
