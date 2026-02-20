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
orchestrator.py          CLI: new-skill, install-skill, list-packs, plugins
config.py                Configuration management
plugins/
  __init__.py            Plugin system (PluginManager, hook lifecycle)
packs/                   Skill packs (domain knowledge for AI agents)
  arcgis/
    skill.json           Pack manifest
    CONTEXT.md           5,600+ line knowledge base
    skills/              Slash commands (arcgis, arcgis-project, etc.)
    projects/            Project templates and briefs
scaffolds/               Templates for generating new skill packs
tests/
  test_orchestrator.py   Unit tests (config, plugins, skill packs)
```

## Testing

```bash
python -m pytest tests/ -v
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
