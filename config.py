#!/usr/bin/env python3
"""
Configuration management for AI Orchestrator.
Handles settings like default LLM, save policies, output directories, etc.
"""
from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field

# Default configuration values
DEFAULT_CONFIG = {
    "llm": {
        "model": "gpt-5",
        "temperature": 1.0,
        "max_retries": 3,
        "cache_enabled": True,
        "cache_ttl_seconds": 86400
    },
    "behavior": {
        "default_save_policy": "A",  # A=Auto, S=Save, D=Delete, K=Keep/ask
        "auto_run": True,
        "verbose_logging": False,
    },
    "paths": {
        "saved_dir": "SAVED",
        "running_dir": "RUNNING",
        "config_dir": "~/.config/ai_orchestrator",
    },
    "security": {
        "prefer_keyring": True,
        "allow_plaintext_fallback": True,  # For development
        "allow_system_actions": True,      # Allow natural OS actions (open/install/update)
        "confirm_system_actions": True     # Ask for confirmation before install/update/remove
    },
    # URL shortcuts for natural commands, e.g. "open email" → gmail URL set by user.
    # Keep empty by default.
    "shortcuts": {}
}

@dataclass
class LLMConfig:
    model: str = "gpt-5"
    temperature: float = 1.0
    max_retries: int = 3
    cache_enabled: bool = True
    cache_ttl_seconds: int = 86400

@dataclass
class BehaviorConfig:
    default_save_policy: str = "A"
    auto_run: bool = True
    verbose_logging: bool = False

@dataclass
class PathsConfig:
    saved_dir: str = "SAVED"
    running_dir: str = "RUNNING"
    config_dir: str = "~/.config/ai_orchestrator"

@dataclass
class SecurityConfig:
    prefer_keyring: bool = True
    allow_plaintext_fallback: bool = True
    allow_system_actions: bool = True
    confirm_system_actions: bool = True

@dataclass
class Config:
    llm: LLMConfig
    behavior: BehaviorConfig
    paths: PathsConfig
    security: SecurityConfig
    shortcuts: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        return cls(
            llm=LLMConfig(**data.get('llm', {})),
            behavior=BehaviorConfig(**data.get('behavior', {})),
            paths=PathsConfig(**data.get('paths', {})),
            security=SecurityConfig(**data.get('security', {})),
            shortcuts=data.get('shortcuts', {}) or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'llm': asdict(self.llm),
            'behavior': asdict(self.behavior),
            'paths': asdict(self.paths),
            'security': asdict(self.security),
            'shortcuts': dict(self.shortcuts or {}),
        }

class ConfigManager:
    def __init__(self, config_file: Optional[Path] = None):
        if config_file is None:
            config_dir = Path(os.path.expanduser(DEFAULT_CONFIG['paths']['config_dir']))
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"
        
        self.config_file = config_file
        self._config = None

    @property
    def config(self) -> Config:
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> Config:
        """Load configuration from file, with defaults for missing values."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                # Merge with defaults
                merged = self._deep_merge(DEFAULT_CONFIG, data)
                return Config.from_dict(merged)
            except Exception as e:
                print(f"Warning: Failed to load config file {self.config_file}: {e}")
                print("Using default configuration.")
        
        return Config.from_dict(DEFAULT_CONFIG)

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            # Set strict permissions (600 for file, 700 for directory)
            try:
                os.chmod(self.config_file, 0o600)
                os.chmod(self.config_file.parent, 0o700)
            except Exception:
                pass
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        current = self.config.to_dict()
        merged = self._deep_merge(current, updates)
        self._config = Config.from_dict(merged)
        self.save_config()

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration."""
        return self.config.llm

    def get_behavior_config(self) -> BehaviorConfig:
        """Get behavior configuration."""
        return self.config.behavior

    def get_paths_config(self) -> PathsConfig:
        """Get paths configuration."""
        return self.config.paths

    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return self.config.security

    def get_shortcuts(self) -> Dict[str, str]:
        return dict(self.config.shortcuts or {})

# Global config manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config() -> Config:
    """Get the current configuration."""
    return get_config_manager().config

# Convenience functions
def get_default_save_policy() -> str:
    return get_config().behavior.default_save_policy

def get_llm_model() -> str:
    return get_config().llm.model

def get_llm_temperature() -> float:
    return get_config().llm.temperature

def get_max_retries() -> int:
    return get_config().llm.max_retries