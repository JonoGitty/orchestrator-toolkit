# Orchestrator Toolkit

Lean middleware for AI coding agents. Sits between AI tools (Claude Code, OpenAI
Codex, Cursor, etc.) and the machine — handling plan execution, multi-stack
building, and plugin-based extensibility.

The AI agents handle reasoning; this handles execution.

## What it does

- Accepts structured plans (JSON with files, deps, and run commands)
- Detects stack: Python, Node.js, Go, Rust, Java, C++
- Installs dependencies and builds automatically
- Creates run scripts and executes projects
- Plugin system for audit, policy, and integrations (e.g. Patchwork/codex-audit)

## Quick start

```bash
git clone https://github.com/JonoGitty/orchestrator-toolkit.git
cd orchestrator-toolkit
pip install -r requirements.txt
```

## Usage

### Generate a project from a prompt

```bash
python orchestrator.py generate "build a FastAPI todo API"
```

### Execute a pre-built plan

```bash
python orchestrator.py execute plan.json
```

### Run an already-built project

```bash
python orchestrator.py run output/my-project
```

### List loaded plugins

```bash
python orchestrator.py plugins
```

## Programmatic API

```python
from orchestrator import generate_plan, execute_plan
from plugins import PluginManager

plugins = PluginManager()
plugins.discover()

plan = generate_plan("build a CLI calculator")
result = execute_plan(plan, plugins=plugins)
print(result["project_dir"], result["stack"], result["run_cmd"])
```

## Plugin system

Plugins are Python modules in `plugins/` that expose a `register(manager)` function.
Hook into the orchestration lifecycle:

| Hook | When | Can modify |
|------|------|------------|
| `pre_execute` | Before plan is applied | plan (return modified) |
| `post_execute` | After plan is applied | — |
| `pre_run` | Before running a project | — |
| `post_run` | After running a project | — |

Example plugin (`plugins/my_plugin.py`):

```python
PLUGIN_NAME = "my-plugin"
PLUGIN_DESCRIPTION = "Logs every execution"

def on_pre_execute(plan, **kwargs):
    print(f"Executing: {plan['name']}")
    return plan

def register(manager):
    manager.add_hook("pre_execute", on_pre_execute)
```

### Patchwork (codex-audit) plugin

Built-in integration with [codex-audit](https://github.com/JonoGitty/codex-audit)
for audit trails and policy enforcement. Install Patchwork and it auto-activates:

```bash
npm install -g patchwork-audit
```

## Configuration

User config: `~/.config/orchestrator-toolkit/config.json`

```json
{
  "llm": {
    "model": "gpt-4.1",
    "temperature": 1.0,
    "max_retries": 3,
    "cache_enabled": true,
    "cache_ttl_seconds": 86400
  },
  "paths": {
    "output_dir": "output",
    "config_dir": "~/.config/orchestrator-toolkit"
  },
  "plugins": {
    "enabled": [],
    "plugin_dir": "plugins"
  }
}
```

## API key setup

For LLM plan generation (first match wins):
1. Local file: `cloud_agent/apikey.txt`
2. Environment variable: `OPENAI_API_KEY`
3. System keyring
4. Config file: `~/.config/orchestrator-toolkit/openai_api_key`

## Testing

```bash
python -m pytest tests/ -v
```

## Supported stacks

Python (venv/poetry/pdm), Node.js (npm/yarn/pnpm), Go, Rust, Java (Gradle/Maven), C++

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
