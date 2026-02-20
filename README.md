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

Skill pack manager for AI coding agents.

Claude Code, Codex, Cursor — they can generate code, but they don't know your
domain. They don't know arcpy gotchas, or that `PolygonToRaster` needs
`CELL_CENTER`, or which UK datasets come from Edina Digimap vs MAGIC.

Orchestrator Toolkit creates and manages **skill packs** — self-contained
domain knowledge bundles that teach AI agents about specific domains. Install a
pack and Claude Code instantly gets slash commands, API patterns, gotchas, and
workflows for that domain.

## How it works

A skill pack is a directory:

```
packs/<name>/
    skill.json              # manifest (name, version, capabilities)
    CONTEXT.md              # domain knowledge (APIs, patterns, gotchas)
    skills/<name>/SKILL.md  # one or more slash commands
    hooks.py                # optional plugin hooks
```

When installed, the SKILL.md and CONTEXT.md files are copied into
`.claude/skills/` so Claude Code auto-discovers them as `/slash-commands`.

## CLI

```bash
# Create a new skill pack from a scaffold
python orchestrator.py new-skill terraform

# Install a pack into Claude Code
python orchestrator.py install-skill arcgis

# List all available packs
python orchestrator.py list-packs

# Show loaded plugins
python orchestrator.py plugins

# Set up patchwork audit + policy enforcement in a project
python orchestrator.py bootstrap

# View the audit trail
python orchestrator.py audit
python orchestrator.py audit --tail 50 --session <session-id>
```

## Shipped pack: ArcGIS Pro

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

## Patchwork — audit trail & policy enforcement

Patchwork is a built-in security layer that hooks into Claude Code's lifecycle.
When bootstrapped into a project, it:

- **Logs every tool call** to `.patchwork/audit.jsonl` (one JSON line per event)
- **Enforces security policies** that deny or warn on dangerous operations
- **Injects context** so Claude Code knows audit is active and respects denials

### Quick start

```bash
# Bootstrap patchwork into your project
cd /path/to/your-project
python /path/to/orchestrator-toolkit/orchestrator.py bootstrap

# View the audit trail
python /path/to/orchestrator-toolkit/orchestrator.py audit
```

Bootstrap creates:

| Path | Purpose |
|------|---------|
| `.patchwork/audit.jsonl` | Append-only audit log |
| `.patchwork/policies/default.yaml` | Security policy rules |
| `.patchwork/config.yaml` | Patchwork configuration |
| `.claude/settings.json` | Claude Code hooks (merged in) |

### Lifecycle hooks

| Event | What happens |
|-------|-------------|
| **SessionStart** | Logs session, injects "patchwork is active" context |
| **PreToolUse** | Checks tool call against policies — deny, warn, or allow |
| **PostToolUse** | Logs what happened (audit trail) |
| **SessionEnd** | Logs session end |

### Security policies

Policies live in `.patchwork/policies/default.yaml` (YAML) or `.json` files.
Each rule matches a tool name (regex) and defines deny/warn patterns:

```yaml
rules:
  - tool: Bash
    deny:
      - pattern: 'rm\s+-[a-zA-Z]*rf[a-zA-Z]*\s+/'
        reason: "Recursive force-delete of root directory blocked"
    warn:
      - pattern: 'sudo\s+'
        reason: "Command uses sudo — elevated privileges"
```

**Shipped deny rules** block: `rm -rf /`, `mkfs`, raw disk writes, `DROP TABLE`,
force push, `chmod 777`, piping remote scripts to shell, writing to `.env` /
credential / private key files, and modifying `.claude/settings.json`.

**Shipped warn rules** flag: `sudo`, package publishing, `git reset --hard`,
`git clean -f`, dependency manifest changes, CI/CD config changes, and reading
sensitive files.

### Audit trail

```bash
# Last 20 entries
python orchestrator.py audit

# Last 50 entries for a specific session
python orchestrator.py audit --tail 50 --session abc123

# Audit log for a different project
python orchestrator.py audit --project /path/to/project
```

Each audit entry is a single JSON line:

```json
{"session":"abc...","event":"pre_tool","tool":"Bash","input":"git status","decision":"allow","ts":"2026-02-20T10:15:30+00:00"}
```

## Building your own pack

```bash
python orchestrator.py new-skill my-domain
```

Creates `packs/my_domain/` with template files ready to fill in:

1. Write your domain knowledge in `CONTEXT.md`
2. Define slash commands in `skills/<name>/SKILL.md`
3. Install: `python orchestrator.py install-skill my-domain`

The manifest (`skill.json`) declares capabilities so tools can filter and
discover packs programmatically.

## Plugins

Plugins hook into the toolkit lifecycle. Drop a `.py` file in `plugins/` with
a `register()` function and it auto-loads.

```python
# plugins/my_logger.py
PLUGIN_NAME = "my-logger"
PLUGIN_DESCRIPTION = "Logs skill pack installs"

def on_pre_execute(plan, **kwargs):
    print(f"[my-logger] Installing: {plan['name']}")
    return plan

def register(manager):
    manager.add_hook("pre_execute", on_pre_execute)
```

Hooks support priority ordering and custom events for skill-to-skill
communication. Plugins auto-discover from four sources: `plugins/` directory,
`skill.json` manifests, installed packages (entry points), and config.

## Setup

```bash
git clone https://github.com/JonoGitty/orchestrator-toolkit.git
cd orchestrator-toolkit
pip install -r requirements.txt
```

Or run the setup script which creates a venv:

```bash
python setup.py
```

## Project structure

```
orchestrator.py          CLI: new-skill, install-skill, list-packs, plugins,
                              bootstrap, audit
config.py                Configuration management
plugins/
  __init__.py            Plugin system (PluginManager, hook lifecycle)
  patchwork.py           Audit trail + policy enforcement hook script
policies/
  default.yaml           Default security policies (deny/warn rules)
packs/                   Skill packs (domain knowledge for AI agents)
  arcgis/
    skill.json           Pack manifest
    CONTEXT.md           5,600+ line knowledge base
    skills/              Slash commands (arcgis, arcgis-project, etc.)
    projects/            Project templates and briefs
scaffolds/               Templates for generating new skill packs
tests/
  test_orchestrator.py   Unit tests (config, plugins, skill packs, patchwork)
```

## Testing

```bash
python -m pytest tests/ -v
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
