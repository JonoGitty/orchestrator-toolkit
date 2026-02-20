```
 ██████╗ ██████╗  ██████╗██╗  ██╗███████╗███████╗████████╗██████╗  █████╗ ████████╗ ██████╗ ██████╗
██╔═══██╗██╔══██╗██╔════╝██║  ██║██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗
██║   ██║██████╔╝██║     ███████║█████╗  ███████╗   ██║   ██████╔╝███████║   ██║   ██║   ██║██████╔╝
██║   ██║██╔══██╗██║     ██╔══██║██╔══╝  ╚════██║   ██║   ██╔══██╗██╔══██║   ██║   ██║   ██║██╔══██╗
╚██████╔╝██║  ██║╚██████╗██║  ██║███████╗███████║   ██║   ██║  ██║██║  ██║   ██║   ╚██████╔╝██║  ██║
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝

 ████████╗ ██████╗  ██████╗ ██╗     ██╗  ██╗██╗████████╗
 ╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██║ ██╔╝██║╚══██╔══╝
    ██║   ██║   ██║██║   ██║██║     █████╔╝ ██║   ██║
    ██║   ██║   ██║██║   ██║██║     ██╔═██╗ ██║   ██║
    ██║   ╚██████╔╝╚██████╔╝███████╗██║  ██╗██║   ██║
    ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝   ╚═╝
```

# Orchestrator Toolkit

The execution layer that sits in the middle between AI coding agents and your machine.

Claude Code, Codex, Cursor — they can all *generate* code. But generating code
and actually getting it built, running, and deployed on a real machine with the
right dependencies, the right stack tooling, and proper audit trails? That's a
different problem. This is the thing that solves it.

## The idea

AI agents are great at reasoning about code. They're bad at the messy stuff:
figuring out which package manager you're using, creating a venv, detecting that
your Vite config references a plugin that isn't in package.json, or making sure
a Go project actually compiles before handing it back to you.

Orchestrator Toolkit is a thin execution middleware that any AI agent can call.
Hand it a structured plan (JSON describing files, dependencies, and a run
command) and it handles the rest — stack detection, dependency installation,
building, launcher creation, and running. It also has a plugin system so you can
bolt on things like audit logging, policy enforcement, or custom build steps.

## What it actually does

**Takes a plan, builds it, runs it.** That's the core loop.

A "plan" is a JSON object describing a project:

```json
{
  "name": "my-api",
  "files": [
    { "filename": "app.py", "code": "from fastapi import FastAPI\n..." },
    { "filename": "requirements.txt", "code": "fastapi\nuvicorn" }
  ],
  "run": "uvicorn app:app --reload"
}
```

The orchestrator then:

1. **Writes the files** to disk in an isolated project directory
2. **Detects the stack** from file contents (Python? Node? Go? Rust? Java? C++?)
3. **Installs dependencies** using the right tool (pip in a venv, npm/yarn/pnpm,
   go mod tidy, cargo build, gradle, maven — it figures it out)
4. **Creates a launcher** (`run.sh`) so the project is immediately runnable
5. **Runs it** if you want

It handles edge cases like:
- Poetry/PDM projects vs plain requirements.txt
- Vite configs that reference plugins not listed in package.json
- Go and Rust compilation with proper binary output
- Java projects across Gradle, Maven, and plain javac
- CMake and raw g++ builds for C++

## How to use it

### From the CLI

```bash
# Generate a project from a prompt (calls an LLM to create the plan)
python orchestrator.py generate "build a FastAPI todo API with SQLite"

# Execute a plan you already have
python orchestrator.py execute plan.json -o ./my-output

# Run an already-built project
python orchestrator.py run output/my-api

# See what plugins are loaded
python orchestrator.py plugins

# Skill pack management
python orchestrator.py new-skill my-domain      # scaffold a new pack
python orchestrator.py install-skill arcgis      # install into Claude Code
python orchestrator.py list-packs                # show available packs
```

### From Python (as a library)

This is designed to be called programmatically by other tools:

```python
from orchestrator import generate_plan, execute_plan, run_project
from plugins import PluginManager
from pathlib import Path

# Set up plugins (auto-discovers from plugins/ directory)
plugins = PluginManager()
plugins.discover()

# Option A: Generate from a prompt via LLM
plan = generate_plan("build a CLI calculator in Rust")
result = execute_plan(plan, plugins=plugins)

# Option B: Pass in your own plan directly
plan = {
    "name": "hello-world",
    "files": [{"filename": "main.py", "code": "print('hello')"}],
    "run": "python main.py"
}
result = execute_plan(plan, output_dir=Path("./builds"), plugins=plugins)

# Result contains everything you need
print(result["project_dir"])  # where the project lives
print(result["stack"])        # "python", "node", "go", etc.
print(result["run_cmd"])      # the resolved run command

# Run it
run_project(Path(result["project_dir"]))
```

## Plugins

Plugins hook into the execution lifecycle. Drop a `.py` file in `plugins/` with
a `register()` function and it auto-loads.

Four hooks are available:

| Hook | Fires when | What it can do |
|------|-----------|---------------|
| `pre_execute` | Before files are written and deps installed | Inspect or modify the plan. Return a modified plan or raise to block. |
| `post_execute` | After the project is fully built | Log results, trigger notifications, run extra validation. |
| `pre_run` | Before a project is executed | Gate execution, set up environment. |
| `post_run` | After a project finishes running | Capture results, clean up. |

### Writing a plugin

```python
# plugins/my_logger.py
PLUGIN_NAME = "my-logger"
PLUGIN_DESCRIPTION = "Logs every plan execution to a file"

def on_pre_execute(plan, **kwargs):
    print(f"[my-logger] Building: {plan['name']} ({len(plan.get('files', []))} files)")
    return plan  # return modified plan, or None to leave it unchanged

def on_post_execute(plan, result, **kwargs):
    print(f"[my-logger] Built at: {result['project_dir']} (stack: {result['stack']})")

def register(manager):
    manager.add_hook("pre_execute", on_pre_execute)
    manager.add_hook("post_execute", on_post_execute)
```

### Built-in: Patchwork (codex-audit) plugin

Ships with an integration for [Patchwork](https://github.com/JonoGitty/codex-audit),
a local-first audit trail system for AI coding agents. When the `patchwork-audit`
CLI is installed on your machine, this plugin auto-activates and:

- **Logs every plan execution** as a tamper-evident audit event
- **Evaluates plans against YAML policies** before execution — can block actions
  that violate your rules (e.g., writing to sensitive files, running dangerous commands)

```bash
# Install Patchwork and the plugin activates automatically
npm install -g patchwork-audit
```

No configuration needed. If Patchwork isn't installed, the plugin silently
disables itself.

## Skill Packs

Skill packs give AI coding agents domain expertise. A pack is a self-contained
directory with a knowledge base (CONTEXT.md), slash commands (SKILL.md files),
and a manifest — when installed, Claude Code picks them up as `/slash-commands`
automatically.

```
packs/<name>/
    skill.json              # manifest (name, version, capabilities)
    CONTEXT.md              # domain knowledge (APIs, patterns, gotchas)
    skills/<name>/SKILL.md  # one or more slash commands
    hooks.py                # optional guardrail hooks
```

### Managing skill packs

```bash
# Create a new skill pack from a scaffold
python orchestrator.py new-skill my-domain

# Install a pack into Claude Code (copies to .claude/skills/)
python orchestrator.py install-skill arcgis

# List all available packs
python orchestrator.py list-packs
```

### Shipped pack: ArcGIS Pro

The first full skill pack covers ArcGIS Pro and arcpy — geospatial analysis,
mapping, geodatabases, and professional map production. Five slash commands:

| Command | What it does |
|---------|-------------|
| `/arcgis` | General arcpy help — spatial analysis, geoprocessing, raster, network analyst |
| `/arcgis-project` | Project management — .aprx structure, maps, layouts, sharing |
| `/arcgis-ingest` | Data ingestion — CSVs, shapefiles, GPX, georeferencing, schema mapping |
| `/arcgis-discover` | Data discovery — scan folders/USBs, match datasets to a project brief |
| `/arcgis-setup` | Environment setup — find ArcGIS Pro install, validate arcpy, configure conda |

Backed by a 5,600+ line CONTEXT.md covering: site suitability analysis,
UK planning workflows, hydrology, 3D analyst, LiDAR, time-series animation,
web GIS / Portal administration, multi-criteria analysis, symbology,
colour palettes, layout automation, and common arcpy gotchas.

### Building your own pack

Use the scaffolding system:

```bash
python orchestrator.py new-skill terraform
```

This creates `packs/terraform/` with template files ready to fill in. See
`scaffolds/` for the templates. The manifest (`skill.json`) declares the pack's
capabilities so tools can filter and discover packs programmatically.

## Supported stacks

| Stack | Detection | Dependency install | Build |
|-------|-----------|-------------------|-------|
| Python | `*.py`, `requirements.txt`, `pyproject.toml` | pip (venv), Poetry, PDM | — |
| Node.js | `package.json`, `*.js`/`*.ts`/`*.tsx` | npm, yarn, pnpm + Vite plugin detection | — |
| Go | `go.mod`, `*.go` | go mod tidy | go build |
| Rust | `Cargo.toml` | — | cargo build --release |
| Java | `build.gradle`, `pom.xml`, `*.java` | Gradle, Maven | javac / jar |
| C++ | `CMakeLists.txt`, `*.cpp`/`*.cc` | — | cmake + make, or g++ |

## Configuration

`~/.config/orchestrator-toolkit/config.json`

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

### API key

The `generate` command needs an LLM API key. First match wins:

1. `cloud_agent/apikey.txt`
2. `OPENAI_API_KEY` environment variable
3. System keyring
4. `~/.config/orchestrator-toolkit/openai_api_key`

If you're only using `execute` (passing in pre-built plans), no API key is needed.

## Setup

```bash
git clone https://github.com/JonoGitty/orchestrator-toolkit.git
cd orchestrator-toolkit
pip install -r requirements.txt
```

Or run the setup script which creates a venv for you:

```bash
python setup.py
```

## Project structure

```
orchestrator.py          Core API + CLI: generate, execute, run, new-skill, install-skill
config.py                Configuration management
cloud_agent/
  cloud_client.py        LLM integration (plan generation, caching, retry)
runtime/
  plan_runner.py         Stack detection, dependency install, building
plugins/
  __init__.py            Plugin system (PluginManager, hook lifecycle)
  patchwork_audit.py     Patchwork/codex-audit integration
packs/                   Skill packs (domain knowledge for AI agents)
  arcgis/
    skill.json           Pack manifest
    CONTEXT.md           5,600+ line knowledge base
    skills/              Slash commands (arcgis, arcgis-project, etc.)
    projects/            Project templates and briefs
scaffolds/               Templates for generating new skill packs
  CONTEXT.md.tpl
  SKILL.md.tpl
  skill.json.tpl
  plugin.py.tpl
utils/
  runner.py              Command execution with JSONL logging
  helper.py              Slugify, safe path joining, run script creation
  backup.py              Project backup snapshots
tests/
  test_orchestrator.py   Unit tests (config, plan parsing, plugins, skill packs)
  test_integration_minimal.py  Integration test (full plan -> build)
```

## Testing

```bash
python -m pytest tests/ -v
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
