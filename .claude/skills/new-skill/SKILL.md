---
name: new-skill
description: Scaffold a new OpenClaw skill plugin with all boilerplate (module, manifest, setup.py, tests)
user-invocable: true
argument-hint: "[skill-name]"
allowed-tools: Bash, Read, Edit
---

# New Skill

Scaffold a complete OpenClaw skill plugin for the orchestrator toolkit.

## Steps

1. Run the scaffold command:

```bash
python orchestrator.py new-skill $ARGUMENTS
```

This generates 4 files:
- `plugins/<slug>.py` — the plugin module with hook stubs
- `plugins/<slug>/skill.json` — metadata manifest
- `plugins/<slug>/setup.py` — for pip-installable distribution
- `tests/test_<slug>.py` — starter test suite

2. Optionally add description and author:

```bash
python orchestrator.py new-skill $0 --description "$1" --author "$2"
```

3. After scaffolding, help the user:
   - Edit the plugin module to implement their hook logic
   - Run the generated tests: `python -m pytest tests/test_<slug>.py -v`
   - Verify it loads: `python orchestrator.py plugins`
