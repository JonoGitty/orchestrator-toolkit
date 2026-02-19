"""
Patchwork Audit plugin — integrates codex-audit (Patchwork) into the
orchestrator lifecycle.

When Patchwork CLI (`patchwork-audit`) is installed, this plugin will:
  - Log plan execution events to the Patchwork audit trail
  - Optionally evaluate plans against Patchwork policies before execution

Install Patchwork:  npm install -g patchwork-audit
Repo:               https://github.com/JonoGitty/codex-audit

If Patchwork is not installed, this plugin silently disables itself.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger("orchestrator.plugins.patchwork")

PLUGIN_NAME = "patchwork-audit"
PLUGIN_DESCRIPTION = "Audit trail & policy enforcement via Patchwork (codex-audit)"

_PATCHWORK_BIN: Optional[str] = None


def _find_patchwork() -> Optional[str]:
    """Locate the patchwork-audit CLI binary."""
    global _PATCHWORK_BIN
    if _PATCHWORK_BIN is not None:
        return _PATCHWORK_BIN or None
    path = shutil.which("patchwork-audit") or shutil.which("patchwork")
    _PATCHWORK_BIN = path or ""
    return path


def _call_patchwork_hook(event: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call a Patchwork hook via stdin/stdout JSON protocol."""
    binary = _find_patchwork()
    if not binary:
        return None
    try:
        proc = subprocess.run(
            [binary, "hook", event],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout.strip())
    except Exception:
        logger.debug("Patchwork hook %s call failed", event, exc_info=True)
    return None


def on_pre_execute(plan: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
    """Notify Patchwork before plan execution. Can block if policy denies."""
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "orchestrator:execute_plan",
        "tool_input": {
            "plan_name": plan.get("name", "unknown"),
            "file_count": len(plan.get("files", [])),
            "files": [f.get("filename", "") for f in plan.get("files", [])],
        },
        "agent": "custom",
        "cwd": ".",
    }
    result = _call_patchwork_hook("pre-tool", payload)
    if result and result.get("allow") is False:
        reason = result.get("reason", "Blocked by Patchwork policy")
        logger.warning("Patchwork BLOCKED plan execution: %s", reason)
        raise PermissionError(f"Patchwork policy denied execution: {reason}")
    return plan


def on_post_execute(plan: Dict[str, Any], result: Dict[str, Any], **kwargs) -> None:
    """Notify Patchwork after plan execution."""
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "orchestrator:execute_plan",
        "tool_input": {
            "plan_name": plan.get("name", "unknown"),
        },
        "tool_response": {
            "project_dir": result.get("project_dir", ""),
            "stack": result.get("stack", ""),
            "run_cmd": result.get("run_cmd", ""),
        },
        "agent": "custom",
        "cwd": ".",
    }
    _call_patchwork_hook("post-tool", payload)


def register(manager) -> None:
    """Register Patchwork hooks with the plugin manager."""
    if not _find_patchwork():
        logger.info("Patchwork CLI not found — plugin disabled (install: npm i -g patchwork-audit)")
        return
    manager.add_hook("pre_execute", on_pre_execute)
    manager.add_hook("post_execute", on_post_execute)
    logger.info("Patchwork audit plugin active")
