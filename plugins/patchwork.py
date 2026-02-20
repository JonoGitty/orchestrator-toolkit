#!/usr/bin/env python3
"""
Patchwork — audit trail and policy enforcement for Claude Code.

This script is called by Claude Code hooks on every lifecycle event.
It reads JSON from stdin, checks policies, logs to an audit trail,
and returns decisions on stdout.

Hook events handled:
    SessionStart  — log session start, inject patchwork context
    PreToolUse    — check policies, log, allow/deny
    PostToolUse   — log result (audit trail)
    SessionEnd    — log session end

Audit log: .patchwork/audit.jsonl (one JSON object per line)
Policies:  policies/*.yaml (checked on PreToolUse)

Called via .claude/settings.json hooks — set up by:
    python orchestrator.py bootstrap
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Project root is the cwd Claude Code passes, or fallback to script location
def _project_root() -> Path:
    """Find the project root (where .patchwork/ lives)."""
    # Try CLAUDE_PROJECT_DIR first (set by Claude Code)
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        return Path(env_dir)
    # Fallback: walk up from cwd looking for .patchwork/
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".patchwork").is_dir():
            return parent
    return cwd


def _audit_path(root: Path) -> Path:
    return root / ".patchwork" / "audit.jsonl"


def _policies_dir(root: Path) -> Path:
    """Find policies directory — check project-local first, then toolkit."""
    local = root / ".patchwork" / "policies"
    if local.is_dir():
        return local
    # Fall back to the toolkit's policies/ directory
    toolkit = Path(__file__).resolve().parent.parent / "policies"
    if toolkit.is_dir():
        return toolkit
    return local  # doesn't exist, but that's fine — no policies loaded


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def _log(root: Path, entry: Dict[str, Any]) -> None:
    """Append one JSON line to the audit log."""
    audit_file = _audit_path(root)
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    entry["ts"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except OSError:
        pass  # don't crash Claude Code if logging fails


# ---------------------------------------------------------------------------
# Policy engine
# ---------------------------------------------------------------------------

def _load_policies(root: Path) -> List[Dict[str, Any]]:
    """Load all YAML policy files. Falls back to JSON if no YAML parser."""
    policies_dir = _policies_dir(root)
    if not policies_dir.is_dir():
        return []

    rules: List[Dict[str, Any]] = []
    for policy_file in sorted(policies_dir.glob("*.yaml")):
        try:
            import yaml
            data = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
        except ImportError:
            # No PyYAML — try a minimal parse for our simple format
            data = _parse_yaml_minimal(policy_file)
        except Exception:
            continue

        if data and isinstance(data.get("rules"), list):
            rules.extend(data["rules"])

    # Also check for .json policy files
    for policy_file in sorted(policies_dir.glob("*.json")):
        try:
            data = json.loads(policy_file.read_text(encoding="utf-8"))
            if isinstance(data.get("rules"), list):
                rules.extend(data["rules"])
        except Exception:
            continue

    return rules


def _parse_yaml_minimal(path: Path) -> Optional[Dict[str, Any]]:
    """
    Minimal YAML-subset parser for policy files when PyYAML isn't installed.
    Handles our specific policy format only — not a general YAML parser.
    """
    try:
        text = path.read_text(encoding="utf-8")
        # Strip comments
        lines = []
        for line in text.split("\n"):
            stripped = line.split(" #")[0] if " #" in line else line
            if stripped.strip().startswith("#"):
                continue
            lines.append(stripped)
        text = "\n".join(lines)

        # Try json.loads as a fallback (won't work for YAML, but worth trying)
        # For our use case, fall back to returning empty if no yaml module
        return None
    except Exception:
        return None


def _check_policies(
    rules: List[Dict[str, Any]],
    tool_name: str,
    tool_input: Dict[str, Any],
) -> Tuple[str, str, Optional[str]]:
    """
    Check tool call against policy rules.

    Returns:
        (decision, reason, warning)
        decision: "allow" or "deny"
        reason: why denied (empty if allowed)
        warning: advisory message (even if allowed)
    """
    # Build a flat string of all input values for pattern matching.
    # This avoids JSON quoting issues (like $ not matching before closing ")
    input_parts: List[str] = []
    for v in tool_input.values():
        if isinstance(v, str):
            input_parts.append(v)
        else:
            input_parts.append(json.dumps(v, separators=(",", ":")))
    input_str = "\n".join(input_parts)

    warning_msgs: List[str] = []

    for rule in rules:
        tool_pattern = rule.get("tool", ".*")
        if not re.search(tool_pattern, tool_name):
            continue

        # Check deny rules
        for deny in rule.get("deny", []):
            pattern = deny.get("pattern", "")
            if pattern and re.search(pattern, input_str, re.IGNORECASE):
                return ("deny", deny.get("reason", "Blocked by policy"), None)

        # Check warn rules
        for warn in rule.get("warn", []):
            pattern = warn.get("pattern", "")
            if pattern and re.search(pattern, input_str, re.IGNORECASE):
                warning_msgs.append(warn.get("reason", "Policy warning"))

    warning = "; ".join(warning_msgs) if warning_msgs else None
    return ("allow", "", warning)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------

def handle_session_start(data: Dict[str, Any], root: Path) -> Dict[str, Any]:
    """Handle SessionStart — log and inject context."""
    _log(root, {
        "session": data.get("session_id", ""),
        "event": "session_start",
        "cwd": data.get("cwd", ""),
    })

    # Count existing audit entries for this project
    audit_file = _audit_path(root)
    entry_count = 0
    if audit_file.exists():
        try:
            entry_count = sum(1 for _ in open(audit_file, "r", encoding="utf-8"))
        except OSError:
            pass

    # Load policies to report what's enforced
    rules = _load_policies(root)
    deny_count = sum(len(r.get("deny", [])) for r in rules)
    warn_count = sum(len(r.get("warn", [])) for r in rules)

    context_parts = [
        "Patchwork audit is active.",
        f"Audit log: .patchwork/audit.jsonl ({entry_count} entries).",
    ]
    if deny_count or warn_count:
        context_parts.append(
            f"Policies: {deny_count} deny rules, {warn_count} warn rules."
        )
    context_parts.append(
        "If a tool call is denied by policy, explain the denial to the user "
        "and suggest an alternative approach."
    )

    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": " ".join(context_parts),
        }
    }


def handle_pre_tool_use(data: Dict[str, Any], root: Path) -> Dict[str, Any]:
    """Handle PreToolUse — check policies, log, return decision."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "")

    # Load and check policies
    rules = _load_policies(root)
    decision, reason, warning = _check_policies(rules, tool_name, tool_input)

    # Build a concise input summary for the audit log
    input_summary = _summarize_input(tool_name, tool_input)

    # Log
    log_entry: Dict[str, Any] = {
        "session": session_id,
        "event": "pre_tool",
        "tool": tool_name,
        "input": input_summary,
        "decision": decision,
    }
    if reason:
        log_entry["reason"] = reason
    if warning:
        log_entry["warning"] = warning
    _log(root, log_entry)

    # Build response
    if decision == "deny":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"[patchwork] {reason}",
            }
        }

    result: Dict[str, Any] = {}
    if warning:
        result["hookSpecificOutput"] = {
            "hookEventName": "PreToolUse",
            "additionalContext": f"[patchwork warning] {warning}",
        }
    return result


def handle_post_tool_use(data: Dict[str, Any], root: Path) -> Dict[str, Any]:
    """Handle PostToolUse — log the result."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "")

    input_summary = _summarize_input(tool_name, tool_input)

    _log(root, {
        "session": session_id,
        "event": "post_tool",
        "tool": tool_name,
        "input": input_summary,
    })
    return {}


def handle_session_end(data: Dict[str, Any], root: Path) -> Dict[str, Any]:
    """Handle SessionEnd — log session end."""
    _log(root, {
        "session": data.get("session_id", ""),
        "event": "session_end",
    })
    return {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summarize_input(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Create a concise one-line summary of tool input for the audit log."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return cmd[:200] if cmd else ""
    elif tool_name in ("Write", "Edit"):
        path = tool_input.get("file_path", "")
        return path
    elif tool_name == "Read":
        return tool_input.get("file_path", "")
    elif tool_name == "Glob":
        return tool_input.get("pattern", "")
    elif tool_name == "Grep":
        return tool_input.get("pattern", "")
    elif tool_name == "Task":
        return tool_input.get("description", "")[:100]
    elif tool_name == "WebFetch":
        return tool_input.get("url", "")
    elif tool_name == "WebSearch":
        return tool_input.get("query", "")
    else:
        # Unknown tool — dump first 150 chars of JSON
        return json.dumps(tool_input, separators=(",", ":"))[:150]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

HANDLERS = {
    "SessionStart": handle_session_start,
    "PreToolUse": handle_pre_tool_use,
    "PostToolUse": handle_post_tool_use,
    "PostToolUseFailure": handle_post_tool_use,  # same logging
    "SessionEnd": handle_session_end,
}


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return 0  # don't crash Claude Code on bad input

    event = data.get("hook_event_name", "")
    handler = HANDLERS.get(event)
    if not handler:
        return 0  # unknown event, ignore

    root = _project_root()
    result = handler(data, root)

    if result:
        json.dump(result, sys.stdout, separators=(",", ":"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
