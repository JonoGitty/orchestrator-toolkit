# Changelog

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
