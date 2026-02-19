"""
{{SKILL_NAME}} — Hooks for the orchestrator plugin system.

This module provides optional Python hooks that fire during the orchestrator
lifecycle. Most skill packs only need SKILL.md + CONTEXT.md for Claude Code
integration. Use hooks when you need programmatic guardrails, validation,
or audit logging.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("orchestrator.plugins.{{SKILL_SLUG}}")

PLUGIN_NAME = "{{SKILL_NAME}}"
PLUGIN_DESCRIPTION = "{{SKILL_DESCRIPTION}}"
PLUGIN_VERSION = "0.1.0"
PLUGIN_DEPENDENCIES: list = []
PLUGIN_CAPABILITIES: list = []


def on_pre_execute(plan: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
    """Called before a plan is applied. Return modified plan or None."""
    logger.info("[{{SKILL_NAME}}] pre_execute: %s", plan.get("name", "?"))
    return None


def on_post_execute(plan: Dict[str, Any], result: Dict[str, Any], **kwargs) -> None:
    """Called after a plan is applied."""
    logger.info("[{{SKILL_NAME}}] post_execute: %s", plan.get("name", "?"))


def register(manager) -> None:
    """Register hooks with the plugin manager."""
    manager.add_hook("pre_execute", on_pre_execute)
    manager.add_hook("post_execute", on_post_execute)
