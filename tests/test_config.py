from pathlib import Path

import pytest

from amta.config import find_workspace_dir, load_config
from amta.errors import AmtaConfigError
from amta.models import ValidationMode


def write_config(workspace_dir: Path, content: str) -> None:
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "config.yml").write_text(content, encoding="utf-8")


def test_load_config_minimal(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".amta"
    write_config(
        workspace_dir,
        """
workspace:
  id: amta-core
  name: AMTA Core
  version: 1
  namespace: hiram
owners:
  - architecture
  - product
""".strip(),
    )

    config = load_config(workspace_dir)

    assert config.workspace.id == "amta-core"
    assert config.workspace.namespace == "hiram"
    assert config.owners == ["architecture", "product"]
    assert config.graph.relation_types == ["depends_on", "impacts"]
    assert config.validation.relation_catalog_mode is ValidationMode.LAX


def test_load_config_with_relation_catalog_strict(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".amta"
    write_config(
        workspace_dir,
        """
workspace:
  id: menu-togo
  name: Menu To Go
  version: 1
  namespace: hiram
owners:
  - architecture
graph:
  relation_types:
    - depends_on
    - impacts
    - blocks
validation:
  relation_catalog_mode: strict
""".strip(),
    )

    config = load_config(workspace_dir)

    assert config.graph.relation_types == ["depends_on", "impacts", "blocks"]
    assert config.validation.relation_catalog_mode is ValidationMode.STRICT


def test_load_config_rejects_missing_config(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".amta"
    workspace_dir.mkdir()

    with pytest.raises(AmtaConfigError, match="config file not found"):
        load_config(workspace_dir)


def test_load_config_rejects_empty_config(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".amta"
    write_config(workspace_dir, "")

    with pytest.raises(AmtaConfigError, match="empty"):
        load_config(workspace_dir)


def test_load_config_rejects_invalid_yaml(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".amta"
    write_config(workspace_dir, "workspace: [")

    with pytest.raises(AmtaConfigError, match="Invalid YAML"):
        load_config(workspace_dir)


def test_load_config_rejects_invalid_model(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".amta"
    write_config(
        workspace_dir,
        """
workspace:
  id: AMTA Core
  name: AMTA Core
  version: 1
owners:
  - architecture
""".strip(),
    )

    with pytest.raises(AmtaConfigError, match="Invalid AMTA config"):
        load_config(workspace_dir)


def test_find_workspace_dir_from_nested_path(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".amta"
    nested_dir = tmp_path / "src" / "package"
    nested_dir.mkdir(parents=True)
    write_config(
        workspace_dir,
        """
workspace:
  id: amta-core
  name: AMTA Core
  version: 1
owners:
  - architecture
""".strip(),
    )

    assert find_workspace_dir(nested_dir) == workspace_dir
