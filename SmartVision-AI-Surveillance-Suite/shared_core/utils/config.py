"""Config loading helpers.

The project is intentionally config-driven: every domain module can override the
shared defaults while still using the same runtime and API layer.
"""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]


def deep_merge(base: dict[str, Any], override: Mapping[str, Any] | None) -> dict[str, Any]:
    """Recursively merge ``override`` into ``base`` without mutating inputs."""

    result = deepcopy(base)
    if not override:
        return result

    for key, value in override.items():
        if (
            isinstance(value, Mapping)
            and isinstance(result.get(key), Mapping)
        ):
            result[key] = deep_merge(dict(result[key]), value)
        else:
            result[key] = deepcopy(value)
    return result


def load_yaml(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config(module_config: str | Path | None = None) -> dict[str, Any]:
    """Load shared defaults, optional module YAML, then environment overrides."""

    load_dotenv(ROOT_DIR / ".env")
    default_config = load_yaml(ROOT_DIR / "shared_core" / "configs" / "default.yaml")
    config = deep_merge(default_config, load_yaml(module_config))

    config.setdefault("app", {})
    config["app"]["environment"] = os.getenv("SMARTVISION_ENV", config["app"].get("environment", "dev"))
    config["app"]["database_url"] = os.getenv(
        "DATABASE_URL",
        config["app"].get("database_url", "sqlite:///data/smartvision.db"),
    )
    config["app"]["database_name"] = os.getenv(
        "MONGODB_DATABASE",
        config["app"].get("database_name", "smartvision_ai_surveillance_suite"),
    )

    config.setdefault("ai", {})
    config["ai"]["device"] = os.getenv("AI_DEVICE", config["ai"].get("device", "auto"))
    config["ai"]["use_half_precision"] = env_bool(
        "AI_HALF_PRECISION",
        bool(config["ai"].get("use_half_precision", True)),
    )

    config.setdefault("dashboard", {})
    config["dashboard"]["api_key"] = os.getenv("SMARTVISION_API_KEY", config["dashboard"].get("api_key", "dev-token"))

    return config
