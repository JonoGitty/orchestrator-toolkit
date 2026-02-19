#!/usr/bin/env python3
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.modules.setdefault("openai", MagicMock())

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
    result = apply_plan(plan, tmp_path)
    project_dir = Path(result["project_dir"])
    assert project_dir.exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "run.sh").exists()
    assert result["run_cmd"].endswith("python main.py")
