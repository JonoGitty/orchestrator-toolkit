---
name: execute-plan
description: Execute an existing plan JSON file to build a project (detect stack, install deps, create run.sh)
user-invocable: true
argument-hint: "[path/to/plan.json]"
allowed-tools: Bash, Read
---

# Execute Plan

Execute a pre-existing plan JSON file to scaffold, install, and build a project.

## Steps

1. If a plan path was provided, execute it directly:

```bash
python orchestrator.py execute $ARGUMENTS
```

2. If no path was provided, help the user find or create a plan JSON. Plans have this structure:

```json
{
  "name": "project-name",
  "description": "What the project does",
  "files": [
    {"filename": "main.py", "code": "print('hello')"}
  ],
  "run": "python main.py",
  "post_install": []
}
```

3. Optionally specify an output directory with `-o <dir>`

4. Review the result: project directory, detected stack, and run command
