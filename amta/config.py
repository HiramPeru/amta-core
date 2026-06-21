"""Workspace configuration loading for AMTA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from yaml import YAMLError

from amta.errors import AmtaConfigError
from amta.models import ConfigModel

WORKSPACE_DIRNAME = ".amta"
CONFIG_FILENAME = "config.yml"


def find_workspace_dir(start: str | Path = ".") -> Path:
    """Find the nearest AMTA workspace directory from a starting path."""
    current = Path(start).resolve()

    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        workspace_dir = candidate / WORKSPACE_DIRNAME
        if workspace_dir.is_dir():
            return workspace_dir

    raise AmtaConfigError(f"AMTA workspace not found from: {current}")


def resolve_config_path(workspace_dir: str | Path | None = None) -> Path:
    """Resolve the config.yml path for a workspace."""
    workspace_path = find_workspace_dir() if workspace_dir is None else Path(workspace_dir)

    config_path = workspace_path / CONFIG_FILENAME

    if not config_path.exists():
        raise AmtaConfigError(f"AMTA config file not found: {config_path}")

    if not config_path.is_file():
        raise AmtaConfigError(f"AMTA config path is not a file: {config_path}")

    return config_path


def load_config(workspace_dir: str | Path | None = None) -> ConfigModel:
    """Load .amta/config.yml into ConfigModel."""
    config_path = resolve_config_path(workspace_dir)

    try:
        raw_config: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        raise AmtaConfigError(f"Invalid YAML in {config_path}: {exc}") from exc

    if raw_config is None:
        raise AmtaConfigError(f"AMTA config file is empty: {config_path}")

    if not isinstance(raw_config, dict):
        raise AmtaConfigError(f"AMTA config root must be a mapping: {config_path}")

    try:
        return ConfigModel.model_validate(raw_config)
    except ValidationError as exc:
        raise AmtaConfigError(f"Invalid AMTA config in {config_path}: {exc}") from exc
