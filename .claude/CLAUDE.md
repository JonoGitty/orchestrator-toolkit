# Orchestrator Toolkit

Skill pack manager for AI coding agents. Creates and manages domain knowledge
packs that teach Claude Code / OpenClaw about specific domains (ArcGIS, Terraform,
data science, etc.). Patchwork (codex-audit) tracks everything.

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
```

Plan execution (CI/headless):
```
orchestrator generate <prompt>       # LLM prompt -> plan -> build
orchestrator execute <plan.json>     # Apply existing plan
orchestrator run <project_dir>       # Run built project
```

## Architecture

- `packs/` — skill pack directory (domain knowledge + SKILL.md)
- `scaffolds/` — templates for generating new skill packs
- `plugins/__init__.py` — PluginManager for hook-based plugins
- `plugins/patchwork_audit.py` — audit trail via codex-audit
- `orchestrator.py` — CLI and core API
- `runtime/plan_runner.py` — plan execution engine
- `config.py` — configuration management

## Key Conventions

- Skill packs live in `packs/` with a `skill.json` manifest
- Hook plugins live in `plugins/` with a `register(manager)` function
- Tests use pytest: `python -m pytest tests/ -v`
