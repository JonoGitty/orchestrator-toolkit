---
name: list-packs
description: List all available skill packs with their capabilities
user-invocable: true
allowed-tools: Bash
---

# List Skill Packs

Show all available domain knowledge packs.

```bash
python orchestrator.py list-packs
```

Each pack can be installed into Claude Code with:
`python orchestrator.py install-skill <name>`
