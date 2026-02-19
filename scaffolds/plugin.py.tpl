"""
{{SKILL_NAME}} — {{SKILL_DESCRIPTION}}

OpenClaw skill plugin for the Orchestrator Toolkit.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("orchestrator.plugins.{{SKILL_SLUG}}")

PLUGIN_NAME = "{{SKILL_NAME}}"
PLUGIN_DESCRIPTION = "{{SKILL_DESCRIPTION}}"
PLUGIN_VERSION = "0.1.0"
PLUGIN_DEPENDENCIES: list = []  # e.g. ["patchwork-audit"]
PLUGIN_CAPABILITIES: list = []  # e.g. ["logging", "validation"]


# ---------------------------------------------------------------------------
# Hook implementations — uncomment/add the hooks you need
# ---------------------------------------------------------------------------

def on_pre_execute(plan: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
    """Called before a plan is applied. Return modified plan or None."""
    logger.info("[{{SKILL_NAME}}] pre_execute: %s", plan.get("name", "?"))
    return None  # Return modified plan dict to alter it, or None to pass through


def on_post_execute(plan: Dict[str, Any], result: Dict[str, Any], **kwargs) -> None:
    """Called after a plan is applied."""
    logger.info(
        "[{{SKILL_NAME}}] post_execute: %s -> %s",
        plan.get("name", "?"),
        result.get("project_dir", "?"),
    )


# def on_pre_run(project_dir, **kwargs):
#     """Called before running a project."""
#     pass


# def on_post_run(project_dir, rc, **kwargs):
#     """Called after running a project."""
#     pass


# def on_detect_stack(files, **kwargs):
#     """Return a stack name string to override detection, or None."""
#     return None


# def on_pre_build(stack, project_dir, plan, **kwargs):
#     """Called before building. Useful for injecting env vars or extra steps."""
#     pass


# def on_post_build(stack, project_dir, result, **kwargs):
#     """Called after building. Useful for validation or metrics."""
#     pass


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register(manager) -> None:
    """Register hooks with the plugin manager."""
    manager.add_hook("pre_execute", on_pre_execute)
    manager.add_hook("post_execute", on_post_execute)
    # Uncomment to enable additional hooks:
    # manager.add_hook("pre_run", on_pre_run)
    # manager.add_hook("post_run", on_post_run)
    # manager.add_hook("detect_stack", on_detect_stack)
    # manager.add_hook("pre_build", on_pre_build)
    # manager.add_hook("post_build", on_post_build)
