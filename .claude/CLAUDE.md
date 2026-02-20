# Orchestrator Toolkit

Skill pack manager for AI coding agents. Creates and manages domain knowledge
packs that teach Claude Code / OpenClaw about specific domains (ArcGIS, Terraform,
data science, etc.).

## What is a skill pack?

A self-contained directory that gives Claude Code domain expertise:

```
packs/<name>/
    skill.json              # manifest (name, version, capabilities)
    CONTEXT.md              # domain knowledge (APIs, patterns, gotchas)
    skills/<name>/SKILL.md  # Claude Code slash command
    hooks.py                # optional Python hooks for guardrails
```

When installed, the SKILL.md + CONTEXT.md are copied into `.claude/skills/`
so Claude Code discovers them as `/slash-commands`.

## CLI Commands

```
orchestrator new-skill <name>        # Create a new skill pack
orchestrator install-skill <name>    # Install into Claude Code
orchestrator list-packs              # Show available packs
orchestrator plugins                 # List loaded hook plugins
orchestrator bootstrap               # Set up patchwork audit + hooks
orchestrator audit                   # View the audit trail
```

## Patchwork Audit

Patchwork is the audit trail and policy enforcement system. When bootstrapped
into a project (`orchestrator bootstrap`), it hooks into Claude Code's lifecycle:

- **SessionStart** — logs session, injects "patchwork is active" context
- **PreToolUse** — checks tool calls against policies, blocks or warns
- **PostToolUse** — logs what happened (audit trail)
- **SessionEnd** — logs session end

Policies live in `.patchwork/policies/default.yaml`. Audit log is at
`.patchwork/audit.jsonl`.

**If a tool call is denied by policy**, explain the denial to the user and
suggest a safe alternative. Do NOT attempt to bypass the policy.

## Architecture

- `packs/` — skill pack directory (domain knowledge + SKILL.md)
- `scaffolds/` — templates for generating new skill packs
- `plugins/__init__.py` — PluginManager for hook-based plugins
- `plugins/patchwork.py` — audit trail + policy enforcement hook script
- `policies/` — default security policy YAML files
- `orchestrator.py` — CLI
- `config.py` — configuration management

## Key Conventions

- Skill packs live in `packs/` with a `skill.json` manifest
- Hook plugins live in `plugins/` with a `register(manager)` function
- Tests use pytest: `python -m pytest tests/ -v`
