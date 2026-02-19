#!/usr/bin/env python3
import os
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.plan_runner import apply_plan


def minimal_plan():
    return {
        "name": "integration-hello",
        "description": "Test project",
        "files": [
            {"filename": "main.py", "code": "print('hello')"},
            {"filename": "requirements.txt", "code": ""},
        ],
        "post_install": [],
        "run": "python main.py",
    }


def test_apply_plan_creates_project(tmp_path):
    plan = minimal_plan()
    result = apply_plan(plan, tmp_path, is_app=True)
    project_dir = Path(result["project_dir"]) 
    assert project_dir.exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "run.sh").exists()
    assert result["run_cmd"].endswith("python main.py")
