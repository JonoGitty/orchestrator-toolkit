---
name: new-skill
description: Create a new domain knowledge skill pack (CONTEXT.md + SKILL.md + manifest)
user-invocable: true
argument-hint: "[skill-name]"
allowed-tools: Bash, Read, Edit, Write
---

# New Skill Pack

Create a new domain knowledge skill pack for the orchestrator toolkit.

## Steps

1. Run the scaffold command:

```bash
python orchestrator.py new-skill $ARGUMENTS
```

This creates a pack in `packs/<name>/` with:
- `skill.json` — manifest with name, version, capabilities
- `CONTEXT.md` — domain knowledge template (fill this in!)
- `skills/<name>/SKILL.md` — Claude Code slash command
- `hooks.py` — optional Python hooks for guardrails
- `tests/test_<name>.py` — pack structure tests

2. Optionally add description and author:

```bash
python orchestrator.py new-skill $0 --description "$1" --author "$2"
```

3. After scaffolding, help the user:
   - Fill in CONTEXT.md with domain knowledge (APIs, patterns, gotchas)
   - Customize the SKILL.md slash command definition
   - Install into Claude Code: `python orchestrator.py install-skill <name>`
