```
 █████╗ ██╗
██╔══██╗██║
███████║██║
██╔══██║██║
██║  ██║██║
╚═╝  ╚═╝╚═╝

 ██████╗ ██████╗  ██████╗ ██╗  ██╗ ███████╗ ███████╗████████╗██████╗  █████╗ ████████╗███████╗
██╔═══██╗██╔══██╗██╔════╝ ██║  ██║ ██╔════╝ ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
██║   ██║██████╔╝██║      ███████║ █████╗   ███████╗   ██║   ██████╔╝███████║   ██║   █████╗  
██║   ██║██╔══██╗██║      ██╔══██║ ██╔══╝   ╚════██║   ██║   ██╔══██╗██╔══██║   ██║   ██╔══╝  
╚██████╔╝██║  ██║╚██████╗ ██║  ██║ ███████╗ ███████║   ██║   ██║  ██║██║  ██║   ██║   ███████╗
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚══════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

AI ORCHESTRATE
AI-powered full system controller
```

AI Orchestrator

A cross-platform AI project generator with an interactive command console.
It turns prompts into runnable projects and can perform a set of system
actions from the same session.

What it does
- Sends your prompt to an LLM (OpenAI GPT-5 by default).
- Parses a structured plan and writes files to disk.
- Detects stack, installs deps, creates launchers, and runs the project.
- Classifies output as PROGRAM vs ONE-OFF to decide where to save it.
- Provides an interactive shell with system commands (apps, wifi, windows, etc).

Platforms
- Linux
- macOS
- Windows (PowerShell and CMD)
- WSL
- GitHub Codespaces

Features
- Project generation: Python, web apps, CLIs, utilities, scripts, games.
- Plan normalization: tolerant JSON parsing with fallback to text wrapping.
- Stack-aware builds: Python (venv), Node (npm/yarn/pnpm), Go, Rust, Java, C++.
- Launchers: run.sh, run.command, run.bat, plus HOW_TO_RUN.txt for apps.
- Save policies: Auto, Save, Delete, Keep (ask after run).
- Interactive commands: history, open/run projects, app launching, wifi, DND.
- Plan cache with TTL (configurable).
- Optional git init and initial commit in generated projects.
- Optional desktop GUI shell with embedded webview (PySide6).

Quick start
1) Clone the repository
   git clone https://github.com/JonoGitty/ai_orchestrator.git
   cd ai_orchestrator

2) Install dependencies
   pip install -r requirements.txt

API key setup
Supported key sources (first match wins):
1) Local file (development): cloud_agent/apikey.txt
2) Environment variable: OPENAI_API_KEY
3) System keyring: service "ai_orchestrator", key "openai_api_key"
4) Config file: ~/.config/ai_orchestrator/openai_api_key

Examples
Linux / macOS (one-shot prompt)
OPENAI_API_KEY="sk-yourkey" python3 orchestrator.py "Make me a GUI app"

Windows PowerShell
$env:OPENAI_API_KEY = "sk-yourkey"; python orchestrator.py "Make me a GUI app"

Windows CMD
set OPENAI_API_KEY=sk-yourkey && python orchestrator.py "Make me a GUI app"

Usage
Interactive session:
  python3 orchestrator.py

One-shot (prompt provided on command line or stdin):
  python3 orchestrator.py "build me a small todo CLI"

You will be prompted for a save policy:
  A = Auto (program -> SAVED, one-off -> RUNNING)
  S = Save
  D = Delete
  K = Keep (ask after run)

Interactive commands (high level)
  /help, /history, /open N, /run N, /prune N
  /apps, /openapp, /openfile, /openpath
  /which, /ps, /stop, /openlast
  /dnd, /wifi, /vpn, /winlist, /focus, /max, /movews
  /setup, /wizard, /sweep

Natural commands also work (examples):
  open chrome
  open ~/Downloads
  volume 40
  brightness 70
  wifi list

Desktop GUI shell (optional)
The GUI shell runs the same core orchestration flow, but adds a log panel and
an embedded webview that can load local app URLs detected from output.

Run:
  python3 gui_shell.py

Dependencies:
  PySide6
  PySide6-QtWebEngine (for QWebEngineView)

Generated projects
Default output locations:
- SAVED/   persistent projects
- RUNNING/ temporary projects

Each project includes:
- run.sh
- run.command
- run.bat
- HOW_TO_RUN.txt (apps only)
- your source files and stack-specific assets

Configuration
User config file:
  ~/.config/ai_orchestrator/config.json

Defaults:
{
  "llm": {
    "model": "gpt-5",
    "temperature": 1.0,
    "max_retries": 3,
    "cache_enabled": true,
    "cache_ttl_seconds": 86400
  },
  "behavior": {
    "default_save_policy": "A",
    "auto_run": true,
    "verbose_logging": false
  },
  "paths": {
    "saved_dir": "SAVED",
    "running_dir": "RUNNING",
    "config_dir": "~/.config/ai_orchestrator"
  },
  "security": {
    "prefer_keyring": true,
    "allow_plaintext_fallback": true,
    "allow_system_actions": true,
    "confirm_system_actions": true
  }
}

Logging and recovery
- LLM retries with exponential backoff.
- Bad replies saved to SAVED/bad_reply.json.
- Runtime logs in orchestrator.log.

Command runner utility
- utils/runner.py provides a unified command runner that logs stdout/stderr to
  runtime/command_log.jsonl. This is a building block for future action
  auditing and confirmation flows.

Docs
- docs/potential-command-runner.md
- docs/potential-terminal-ui.md

Backup CLI
The separate CLI wrapper provides backup commands:
  python3 orchestrator_cli.py
  /backup
  /install-nightly-backup [HH:MM]
  /uninstall-nightly-backup

Changelog
See CHANGELOG.md.

Testing
python -m pytest -v
