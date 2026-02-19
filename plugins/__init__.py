"""
Orchestrator Toolkit — Plugin / Skill System.

Plugins (skills) are Python modules that expose a ``register(manager)`` function.
Each plugin can hook into the orchestration lifecycle via built-in **and** custom
events.

Built-in hooks:
    - pre_execute(plan)           -> before a plan is applied; can modify the plan
    - post_execute(plan, result)  -> after a plan is applied
    - pre_run(project_dir)        -> before running a project
    - post_run(project_dir, rc)   -> after running a project
    - detect_stack(files)         -> contribute to stack detection
    - pre_build(stack, project_dir, plan)  -> before building
    - post_build(stack, project_dir, result) -> after building

Plugins can also register **custom** hook events for skill-to-skill communication.

Discovery sources (in order):
    1. ``plugins/`` directory (any .py with a ``register()`` function)
    2. ``skill.json`` manifests in plugin directories
    3. Installed packages advertising ``orchestrator.plugins`` entry points
    4. Explicitly listed in ``config.plugins.enabled``

Example plugin (``plugins/my_plugin.py``):

    PLUGIN_NAME = "my-plugin"
    PLUGIN_DESCRIPTION = "Does something useful"

    def on_pre_execute(plan, **kw):
        print(f"About to execute: {plan.get('name')}")
        return plan

    def register(manager):
        manager.add_hook("pre_execute", on_pre_execute)
"""
from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("orchestrator.plugins")

# Built-in lifecycle hook names
BUILTIN_HOOKS: Tuple[str, ...] = (
    "pre_execute",
    "post_execute",
    "pre_run",
    "post_run",
    "detect_stack",
    "pre_build",
    "post_build",
)

# Kept for backwards-compat with tests that reference HOOK_NAMES
HOOK_NAMES = BUILTIN_HOOKS


class PluginManager:
    """Central registry for plugins (skills), hooks, and metadata."""

    def __init__(self) -> None:
        self._hooks: Dict[str, List[Tuple[int, Callable]]] = {
            name: [] for name in BUILTIN_HOOKS
        }
        self._plugins: List[Dict[str, Any]] = []
        self._loaded_names: Set[str] = set()

    # ------------------------------------------------------------------
    # Hook management
    # ------------------------------------------------------------------

    def register_hook_type(self, event: str) -> None:
        """Register a custom hook event name (for skill-to-skill comms)."""
        if event not in self._hooks:
            self._hooks[event] = []
            logger.debug("Registered custom hook type: %s", event)

    def add_hook(
        self, event: str, callback: Callable, *, priority: int = 100
    ) -> None:
        """Add a callback for *event*.

        Lower ``priority`` values run first (default 100).
        If *event* is unknown it is automatically registered as a custom hook.
        """
        if event not in self._hooks:
            self.register_hook_type(event)
        self._hooks[event].append((priority, callback))
        # Keep sorted by priority so fire order is deterministic
        self._hooks[event].sort(key=lambda t: t[0])

    def hook(self, event: str, **kwargs: Any) -> Any:
        """Fire all callbacks for *event*. Returns the last non-None result."""
        result = None
        for _prio, cb in self._hooks.get(event, []):
            try:
                ret = cb(**kwargs)
                if ret is not None:
                    result = ret
            except Exception:
                logger.exception(
                    "Plugin hook %s raised an error in %s", event, cb
                )
        return result

    def get_hook_names(self) -> List[str]:
        """Return all registered hook names (built-in + custom)."""
        return list(self._hooks.keys())

    # ------------------------------------------------------------------
    # Plugin registration
    # ------------------------------------------------------------------

    def register_plugin(
        self,
        name: str,
        description: str = "",
        *,
        version: str = "0.0.0",
        author: str = "",
        dependencies: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a plugin with rich metadata."""
        if name in self._loaded_names:
            logger.debug("Plugin %s already registered — skipping", name)
            return
        entry: Dict[str, Any] = {
            "name": name,
            "description": description,
            "version": version,
            "author": author,
            "dependencies": dependencies or [],
            "capabilities": capabilities or [],
        }
        if metadata:
            entry["metadata"] = metadata
        self._plugins.append(entry)
        self._loaded_names.add(name)
        logger.info("Registered plugin: %s v%s", name, version)

    def list_plugins(self) -> List[Tuple[str, str]]:
        """Return ``[(name, description), ...]`` for all registered plugins.

        Preserves the simple tuple interface used by CLI and tests.
        """
        return [(p["name"], p["description"]) for p in self._plugins]

    def list_plugins_detailed(self) -> List[Dict[str, Any]]:
        """Return full metadata dicts for all registered plugins."""
        return list(self._plugins)

    def get_plugin(self, name: str) -> Optional[Dict[str, Any]]:
        """Lookup a plugin by name."""
        for p in self._plugins:
            if p["name"] == name:
                return p
        return None

    # ------------------------------------------------------------------
    # Dependency resolution
    # ------------------------------------------------------------------

    def check_dependencies(self) -> List[str]:
        """Return a list of unmet dependency names."""
        missing: List[str] = []
        for p in self._plugins:
            for dep in p.get("dependencies", []):
                if dep not in self._loaded_names:
                    missing.append(f"{p['name']} requires {dep}")
        return missing

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self, plugin_dir: Optional[Path] = None) -> None:
        """Auto-discover plugins from multiple sources."""
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent

        # 1. Python modules in plugins/ directory
        self._discover_directory(plugin_dir)

        # 2. skill.json manifests in plugin sub-directories
        self._discover_skill_manifests(plugin_dir)

        # 3. Installed packages via entry points
        self._discover_entry_points()

        # 4. Explicitly configured plugins
        self._discover_configured()

        # Check dependencies
        problems = self.check_dependencies()
        for problem in problems:
            logger.warning("Unmet plugin dependency: %s", problem)

    def _discover_directory(self, plugin_dir: Path) -> None:
        """Load .py plugin modules from a directory."""
        for py_file in sorted(plugin_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"plugins.{py_file.stem}"
            self._load_module(module_name, source=str(py_file))

    def _discover_skill_manifests(self, plugin_dir: Path) -> None:
        """Load plugins that have a skill.json manifest."""
        for manifest_file in sorted(plugin_dir.rglob("skill.json")):
            try:
                manifest = json.loads(
                    manifest_file.read_text(encoding="utf-8")
                )
                name = manifest.get("name", manifest_file.parent.name)
                if name in self._loaded_names:
                    continue

                entry_module = manifest.get("entry_module")
                if entry_module:
                    self._load_module(entry_module, source=str(manifest_file))

                # Register with manifest metadata regardless
                self.register_plugin(
                    name=name,
                    description=manifest.get("description", ""),
                    version=manifest.get("version", "0.0.0"),
                    author=manifest.get("author", ""),
                    dependencies=manifest.get("dependencies", []),
                    capabilities=manifest.get("capabilities", []),
                    metadata=manifest,
                )
            except Exception:
                logger.exception(
                    "Failed to load skill manifest: %s", manifest_file
                )

    def _discover_entry_points(self) -> None:
        """Discover plugins installed as packages with entry points."""
        try:
            if hasattr(importlib, "metadata"):
                meta = importlib.metadata  # type: ignore[attr-defined]
            else:
                import importlib.metadata as meta  # type: ignore[no-redef]

            eps = meta.entry_points()
            # Python 3.12+ returns a SelectableGroups / dict
            if hasattr(eps, "select"):
                plugin_eps = eps.select(group="orchestrator.plugins")
            elif isinstance(eps, dict):
                plugin_eps = eps.get("orchestrator.plugins", [])
            else:
                plugin_eps = [
                    ep for ep in eps if ep.group == "orchestrator.plugins"
                ]

            for ep in plugin_eps:
                try:
                    register_fn = ep.load()
                    register_fn(self)
                    if ep.name not in self._loaded_names:
                        self.register_plugin(
                            name=ep.name,
                            description=f"Entry-point plugin: {ep.value}",
                        )
                except Exception:
                    logger.exception(
                        "Failed to load entry-point plugin: %s", ep.name
                    )
        except Exception:
            logger.debug("Entry-point discovery not available", exc_info=True)

    def _discover_configured(self) -> None:
        """Load plugins explicitly listed in config."""
        try:
            from config import get_config

            for module_name in get_config().plugins.enabled:
                self._load_module(module_name, source="config")
        except Exception:
            pass

    def _load_module(self, module_name: str, source: str = "") -> None:
        """Import a module and call its register() function."""
        try:
            mod = importlib.import_module(module_name)
            if hasattr(mod, "register"):
                mod.register(self)
                name = getattr(mod, "PLUGIN_NAME", module_name.split(".")[-1])
                desc = getattr(mod, "PLUGIN_DESCRIPTION", "")
                version = getattr(mod, "PLUGIN_VERSION", "0.0.0")
                deps = getattr(mod, "PLUGIN_DEPENDENCIES", [])
                caps = getattr(mod, "PLUGIN_CAPABILITIES", [])
                self.register_plugin(
                    name=name,
                    description=desc,
                    version=version,
                    dependencies=deps,
                    capabilities=caps,
                )
        except Exception:
            logger.exception(
                "Failed to load plugin module: %s (source: %s)",
                module_name,
                source,
            )
