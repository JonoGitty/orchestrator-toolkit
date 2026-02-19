"""
Orchestrator Toolkit — Plugin System.

Plugins are Python modules that expose a `register(manager)` function.
Each plugin can hook into the orchestration lifecycle:

    - pre_execute(plan)   -> called before a plan is applied; can modify the plan
    - post_execute(plan, result)  -> called after a plan is applied
    - pre_run(project_dir) -> called before running a project
    - post_run(project_dir, return_code) -> called after running a project

Example plugin (plugins/my_plugin.py):

    PLUGIN_NAME = "my-plugin"
    PLUGIN_DESCRIPTION = "Does something useful"

    def on_pre_execute(plan):
        print(f"About to execute: {plan.get('name')}")
        return plan  # return modified plan or None to keep original

    def register(manager):
        manager.add_hook("pre_execute", on_pre_execute)

Plugins are discovered from:
    1. The plugins/ directory (any .py file with a register() function)
    2. Explicitly listed in config.plugins.enabled
"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("orchestrator.plugins")

HOOK_NAMES = ("pre_execute", "post_execute", "pre_run", "post_run")


class PluginManager:
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {name: [] for name in HOOK_NAMES}
        self._plugins: List[Tuple[str, str]] = []  # (name, description)

    def add_hook(self, event: str, callback: Callable) -> None:
        if event not in self._hooks:
            raise ValueError(f"Unknown hook event: {event!r}. Must be one of {HOOK_NAMES}")
        self._hooks[event].append(callback)

    def hook(self, event: str, **kwargs) -> Any:
        """Fire all callbacks for an event. Returns the last non-None result."""
        result = None
        for cb in self._hooks.get(event, []):
            try:
                ret = cb(**kwargs)
                if ret is not None:
                    result = ret
            except Exception:
                logger.exception("Plugin hook %s raised an error in %s", event, cb)
        return result

    def register_plugin(self, name: str, description: str = "") -> None:
        self._plugins.append((name, description))
        logger.info("Registered plugin: %s", name)

    def list_plugins(self) -> List[Tuple[str, str]]:
        return list(self._plugins)

    def discover(self, plugin_dir: Optional[Path] = None) -> None:
        """Auto-discover plugins from the plugins/ directory."""
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent

        for py_file in sorted(plugin_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"plugins.{py_file.stem}"
            try:
                mod = importlib.import_module(module_name)
                if hasattr(mod, "register"):
                    mod.register(self)
                    name = getattr(mod, "PLUGIN_NAME", py_file.stem)
                    desc = getattr(mod, "PLUGIN_DESCRIPTION", "")
                    self.register_plugin(name, desc)
            except Exception:
                logger.exception("Failed to load plugin: %s", module_name)

        # Also load explicitly configured plugins
        try:
            from config import get_config
            for module_name in get_config().plugins.enabled:
                try:
                    mod = importlib.import_module(module_name)
                    if hasattr(mod, "register"):
                        mod.register(self)
                        name = getattr(mod, "PLUGIN_NAME", module_name)
                        desc = getattr(mod, "PLUGIN_DESCRIPTION", "")
                        self.register_plugin(name, desc)
                except Exception:
                    logger.exception("Failed to load configured plugin: %s", module_name)
        except Exception:
            pass
