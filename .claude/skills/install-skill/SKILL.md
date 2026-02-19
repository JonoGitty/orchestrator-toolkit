---
name: install-skill
description: Install a skill pack into Claude Code so it appears as a /slash-command
user-invocable: true
argument-hint: "[pack-name]"
allowed-tools: Bash
---

# Install Skill Pack

Install a skill pack from `packs/` into `.claude/skills/` so Claude Code discovers it.

```bash
python orchestrator.py install-skill $ARGUMENTS
```

After installation, the skill appears as a `/slash-command` in Claude Code.

To see available packs first: `python orchestrator.py list-packs`
