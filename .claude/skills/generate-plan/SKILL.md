---
name: generate-plan
description: Generate an execution plan and build a project from a natural-language prompt using the orchestrator
user-invocable: true
argument-hint: "[project description]"
allowed-tools: Bash, Read
---

# Generate Plan

Generate and build a project from a natural-language description using the orchestrator toolkit.

## Steps

1. Run the orchestrator generate command:

```bash
python orchestrator.py generate $ARGUMENTS
```

2. Review the output for:
   - `Project ready: <path>` — the generated project directory
   - `Stack: <name>` — the detected technology stack
   - `Run: <command>` — how to run the built project

3. If the user wants to run it immediately, use `python orchestrator.py run <project_dir>`

4. If the plan needs tweaks, the plan JSON is written to the output directory and can be edited and re-executed with `/execute-plan`
