---
name: list-plugins
description: List all loaded orchestrator plugins with version, dependencies, and capabilities
user-invocable: true
allowed-tools: Bash
---

# List Plugins

Show all loaded orchestrator plugins with their metadata.

```bash
python orchestrator.py plugins
```

Output includes:
- Plugin name and version
- Description
- Dependencies (other plugins required)
- Capabilities (what the plugin provides)
- Any custom hook events registered
