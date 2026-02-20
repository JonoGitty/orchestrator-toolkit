# Changelog

## v0.5.0 — Patchwork Audit Trail & Policy Enforcement

Re-introduces patchwork as a Claude Code hooks-based audit and security layer.
Every tool call is logged and checked against configurable security policies.

### Added
- **`plugins/patchwork.py`** — hook handler script called by Claude Code on
  every lifecycle event (SessionStart, PreToolUse, PostToolUse, SessionEnd)
- **`policies/default.yaml`** — shipped security policies with deny/warn rules:
  - Deny: `rm -rf /`, `mkfs`, raw disk writes, `DROP TABLE/DATABASE`,
    `TRUNCATE TABLE`, force push, `chmod 777`, piping remote scripts to shell,
    writing `.env` / credential / private key files, modifying
    `.claude/settings.json`
  - Warn: `sudo`, package publishing, `git reset --hard`, `git clean -f`,
    dependency manifest changes, CI/CD config changes, reading `.env` or
    private key files
- **`orchestrator.py bootstrap`** — one command wires patchwork into any project:
  creates `.patchwork/` directory, copies default policies, merges hooks into
  `.claude/settings.json`, updates `.gitignore` and `CLAUDE.md`
- **`orchestrator.py audit`** — pretty-prints the audit trail with session
  filtering (`--session`) and tail control (`--tail`)
- **30 new tests** across 6 test classes covering policies, audit logging,
  hook handlers, input summarization, bootstrap, and default policy validation

### Changed
- `orchestrator.py` expanded with bootstrap and audit CLI subcommands
- `.claude/CLAUDE.md` updated with patchwork documentation
- `README.md` updated with full patchwork section (lifecycle hooks, policies,
  audit trail usage, project structure)

## v0.4.0 — Strip to Core

Removed the plan execution engine. Claude Code already handles building and
running projects — the toolkit now focuses purely on skill pack management
and the plugin system.

### Removed
- Plan execution engine (`runtime/plan_runner.py`) — stack detection, dep
  install, building, launchers
- LLM integration (`cloud_agent/`) — plan generation via OpenAI
- `generate`, `execute`, `run` CLI commands
- Patchwork audit plugin (hooks only fired during plan execution)
- `utils/runner.py`, `utils/helper.py`, `utils/backup.py`
- `local_agent/` directory (leftover from v0.1.0)
- `scripts/` directory (backup systemd timers)
- LLM and security config sections
- `openai` and `keyring` dependencies

### Changed
- `orchestrator.py` stripped from ~280 to ~170 lines — skill pack CLI only
- `config.py` simplified to plugins config only
- README rewritten around skill packs as the core value proposition
- Test suite cleaned — removed plan parsing and integration tests
- `setup.py` simplified — no more API key setup instructions

## v0.3.0 — Skill Pack System + ArcGIS Domain Pack

New skill pack architecture that gives AI coding agents domain expertise via
installable knowledge packs.

### Added
- **Skill pack system** — self-contained packs with CONTEXT.md, SKILL.md slash
  commands, and a skill.json manifest
- **Scaffolding** — `new-skill` command generates a pack from templates
- **Pack management CLI** — `install-skill`, `list-packs` commands
- **ArcGIS Pro skill pack** (v0.5.0) — full geospatial domain pack:
  - 5,600+ line CONTEXT.md covering arcpy, spatial analysis, geoprocessing,
    raster, network analyst, spatial statistics, geocoding
  - UK planning & site suitability workflows (multi-criteria analysis,
    PolygonToRaster, Reclassify, weighted overlay)
  - Hydrology, 3D Analyst, LiDAR, time-series animation
  - Web GIS, Portal administration, hosted feature services
  - Symbology engine, colour palettes, layer visibility
  - Layout automation and professional map production
  - Project templates with BRIEF.md, DATASETS.md, PARAMETERS.md
  - 5 slash commands: /arcgis, /arcgis-project, /arcgis-ingest,
    /arcgis-discover, /arcgis-setup
- **Claude Code integration** — CLAUDE.md project instructions, .claude/skills/
  directory, settings.json with tool permissions
- **Plugin scaffolding** — `new-skill` also generates plugin templates with tests

### Changed
- README rewritten with skill pack documentation
- Test suite expanded with skill pack and scaffolding tests
- .gitignore updated for skill pack development

## v0.2.0 — Middleware Refactor

Major refactor: stripped down from a monolithic app-builder/system-controller
to a lean orchestration middleware for AI coding agents.

### Removed
- Desktop GUI shell (gui_shell.py, PySide6)
- System control: audio, brightness, bluetooth, screenshots, display, wifi, VPN, DND
- Natural language command translation (~1200 lines)
- Interactive shell with 40+ slash commands
- Email/calendar integrations (IMAP, CalDAV)
- Terminal dashboard (curses UI)
- App builder classification (PROGRAM vs ONE_OFF)
- Save policies (Auto/Save/Delete/Keep)
- Desktop app enumeration and launcher writing
- Window management (wmctrl)

### Added
- Plugin system with lifecycle hooks (pre_execute, post_execute, pre_run, post_run)
- Patchwork (codex-audit) plugin for audit trails and policy enforcement
- Clean CLI with subcommands: generate, execute, run, plugins
- Programmatic API: generate_plan(), execute_plan(), run_project()

### Changed
- orchestrator.py: 2016 lines -> ~170 lines
- Config simplified: removed behavior, shortcuts, system actions
- System prompt updated for middleware use case
- Output directory: SAVED/RUNNING -> output/
- Requirements stripped to essentials (openai, keyring, pytest)

## v0.1.0 — Initial Release

- Full-featured AI app builder and system controller
- LLM plan generation, multi-stack builds, interactive shell
