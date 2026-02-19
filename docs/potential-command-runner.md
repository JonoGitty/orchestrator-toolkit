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

POTENTIAL IDEA: Unified Command Runner + Action Layers

Status: Concept sketch only. Not implemented.

Goal
Unify all command execution (user commands, AI actions, and build/install steps)
through a single "command runner" so output can be captured, logged, and gated
by a permission policy. This keeps the current behavior but adds visibility and
control.

Non-goals
- Not replacing existing commands or flows.
- Not changing the LLM prompt/plan format.
- Not locking the project to one OS.

High-level components
1) User Command Layer
   - Slash commands and natural language commands remain as-is.
   - Each action calls the runner instead of subprocess directly.

2) AI Action Layer
   - Maps AI intent to action sequences (e.g., wifi connect -> list -> connect).
   - Uses the same runner so stdout/stderr are visible to the AI.

3) Project Builder Layer
   - Existing plan -> apply_plan flow stays intact.
   - All install/build steps call the runner for logging + gating.

Command runner (core idea)
Function signature (sketch):
  run_cmd(cmd, *, cwd=None, env=None, mode="read"|"write", confirm=True)

Behavior:
- Captures stdout/stderr.
- Logs: timestamp, command, cwd, exit code, output.
- Applies policy:
  - "read" or safe commands auto-run.
  - "write" or risky commands prompt/confirm.
- Returns output so the caller (including AI) can reason on it.

Where it fits today
- orchestrator.py:
  Replace subprocess usage in wifi/audio/brightness/window/app ops,
  /ps, /which, /apps, /openapp, etc.
- runtime/plan_runner.py:
  Replace _run() and installer/build calls with run_cmd().

Logging
- Log file suggestion: runtime/command_log.jsonl
- One JSON object per command with stdout/stderr truncated if large.

Benefits
- AI can "see" terminal output, enabling safer/autonomous decisions.
- Centralized audit trail for all actions.
- Consistent permission prompts for risky operations.

Risks / mitigations
- Over-prompting: classify safe commands + allow user overrides.
- Sensitive data in logs: redact known tokens, allow log disable.

Next steps (optional)
1) Add a minimal runner module with logging only.
2) Wire a few low-risk commands to it.
3) Expand coverage to plan_runner installers/builds.
