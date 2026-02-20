#!/usr/bin/env python3
"""
Configuration management for Orchestrator Toolkit.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_CONFIG = {
    "plugins": {
        "enabled": [],
        "disabled": [],
        "plugin_dir": "plugins",
        "discover_entry_points": True,
    },
}


@dataclass
class PluginsConfig:
    enabled: List[str] = field(default_factory=list)
    disabled: List[str] = field(default_factory=list)
    plugin_dir: str = "plugins"
    discover_entry_points: bool = True


@dataclass
class Config:
    plugins: PluginsConfig

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Config:
        return cls(
            plugins=PluginsConfig(**data.get("plugins", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugins": asdict(self.plugins),
        }


class ConfigManager:
    def __init__(self, config_file: Optional[Path] = None):
        if config_file is None:
            config_dir = Path(os.path.expanduser("~/.config/orchestrator-toolkit"))
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"
        self.config_file = config_file
        self._config: Optional[Config] = None

    @property
    def config(self) -> Config:
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> Config:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                merged = self._deep_merge(DEFAULT_CONFIG, data)
                return Config.from_dict(merged)
            except Exception as e:
                print(f"Warning: Failed to load config {self.config_file}: {e}")
        return Config.from_dict(DEFAULT_CONFIG)

    def save_config(self) -> None:
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.config.to_dict(), f, indent=2)
            try:
                os.chmod(self.config_file, 0o600)
            except Exception:
                pass
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_config(self, updates: Dict[str, Any]) -> None:
        current = self.config.to_dict()
        merged = self._deep_merge(current, updates)
        self._config = Config.from_dict(merged)
        self.save_config()

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


# Global singleton
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> Config:
    return get_config_manager().config
