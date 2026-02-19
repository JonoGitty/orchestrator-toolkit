# Orchestrator Toolkit

Lean execution middleware for AI coding agents. Sits between AI reasoning (Claude Code, Codex, Cursor) and the machine.

## Architecture

- `orchestrator.py` — CLI entry point, core API (`generate_plan`, `execute_plan`, `run_project`)
- `plugins/__init__.py` — PluginManager with hook lifecycle, custom events, dependency resolution
- `runtime/plan_runner.py` — Stack detection, dependency install, build, run.sh generation
- `config.py` — Dataclass-based config with JSON file support
- `cloud_agent/` — LLM plan generation via OpenAI
- `scaffolds/` — Skill templates for `orchestrator new-skill`

## Plugin / Skill System

Plugins hook into 7 lifecycle events via `PluginManager.add_hook(event, callback, priority=N)`:

| Hook | Fires when | Can return |
|------|-----------|------------|
| `pre_execute` | Before plan applied | Modified plan dict |
| `post_execute` | After plan applied | — |
| `pre_run` | Before project runs | — |
| `post_run` | After project runs | — |
| `detect_stack` | During stack detection | Stack name string |
| `pre_build` | Before dep install/build | — |
| `post_build` | After build completes | — |

Plugins can also register **custom** hook events for skill-to-skill communication.

## CLI Commands

```
orchestrator generate <prompt>       # LLM prompt -> plan -> build
orchestrator execute <plan.json>     # Apply existing plan JSON
orchestrator run <project_dir>       # Run built project
orchestrator plugins                 # List loaded plugins with metadata
orchestrator new-skill <name>        # Scaffold a new skill plugin
```

## Stack Detection

Auto-detects: python (pip/poetry/pdm), node (npm/yarn/pnpm + Vite), go, rust, java-gradle, java-maven, java-plain, cpp, generic.

## Key Conventions

- Plugin modules live in `plugins/` with a `register(manager)` function
- `skill.json` manifests provide rich metadata (version, deps, capabilities)
- Entry-point packages (`orchestrator.plugins` group) are auto-discovered
- Tests use pytest: `python -m pytest tests/ -v`
- Config lives at `~/.config/orchestrator-toolkit/config.json`
