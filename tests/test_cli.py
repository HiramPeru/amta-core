from pathlib import Path

from typer.testing import CliRunner

from amta.cli import app

runner = CliRunner()


def test_cli_init_creates_workspace(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "--path",
            str(tmp_path),
            "--workspace-id",
            "amta-core",
            "--workspace-name",
            "AMTA Core",
            "--namespace",
            "hiram",
        ],
    )

    assert result.exit_code == 0
    assert "PASS" in result.output
    assert (tmp_path / ".amta" / "config.yml").exists()
    assert (tmp_path / ".amta" / "nodes").is_dir()
    assert (tmp_path / ".amta" / "generated").is_dir()
    assert (tmp_path / ".amta" / "cache").is_dir()


def test_cli_init_fails_if_workspace_exists(tmp_path: Path) -> None:
    first = runner.invoke(app, ["init", "--path", str(tmp_path)])
    second = runner.invoke(app, ["init", "--path", str(tmp_path)])

    assert first.exit_code == 0
    assert second.exit_code == 1
    assert "workspace already exists" in second.output


def test_cli_validate_passes_on_empty_workspace(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_path)])

    result = runner.invoke(app, ["validate", "--path", str(tmp_path)])

    assert result.exit_code == 0
    assert "PASS" in result.output


def test_cli_validate_with_one_orphan_returns_warn(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_path)])
    node_path = tmp_path / ".amta" / "nodes" / "DEC-001.md"
    node_path.write_text(
        """
---
id: DEC-001
type: decision
status: active
title: First Decision
summary: First decision summary.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations: []
---

Body.
""".lstrip(),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate", "--path", str(tmp_path)])

    assert result.exit_code == 2
    assert "WARN" in result.output
    assert "VAL-W001" in result.output


def test_cli_build_generates_artifacts(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_path)])
    nodes_dir = tmp_path / ".amta" / "nodes"
    (nodes_dir / "DEC-001.md").write_text(
        """
---
id: DEC-001
type: decision
status: active
title: First Decision
summary: First decision summary.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations:
  - type: impacts
    target: MOD-001
---

Body.
""".lstrip(),
        encoding="utf-8",
    )
    (nodes_dir / "MOD-001.md").write_text(
        """
---
id: MOD-001
type: module
status: active
title: Core Module
summary: Core module summary.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations: []
---

Body.
""".lstrip(),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["build", "--path", str(tmp_path)])

    assert result.exit_code == 0
    assert "PASS" in result.output
    assert (tmp_path / ".amta" / "generated" / "GRAPH.json").exists()
    assert (tmp_path / ".amta" / "generated" / "MANIFEST.json").exists()
    assert (tmp_path / ".amta" / "generated" / "STATE.md").exists()
    assert (tmp_path / ".amta" / "generated" / "ROADMAP.md").exists()
    assert (tmp_path / ".amta" / "generated" / "CHANGELOG.md").exists()


def test_cli_schemas_generates_json_schemas(tmp_path: Path) -> None:
    result = runner.invoke(app, ["schemas", "--output", str(tmp_path)])

    assert result.exit_code == 0
    assert "PASS: wrote" in result.output
    assert (tmp_path / "node.schema.json").exists()
    assert (tmp_path / "config.schema.json").exists()
    assert (tmp_path / "graph.schema.json").exists()

def test_cli_query_downstream(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_path)])
    nodes_dir = tmp_path / ".amta" / "nodes"

    (nodes_dir / "DEC-001.md").write_text(
        """
---
id: DEC-001
type: decision
status: active
title: First Decision
summary: First decision summary.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations:
  - type: impacts
    target: MOD-001
---

Body.
""".lstrip(),
        encoding="utf-8",
    )

    (nodes_dir / "MOD-001.md").write_text(
        """
---
id: MOD-001
type: module
status: active
title: Core Module
summary: Core module summary.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations:
  - type: depends_on
    target: TSK-001
---

Body.
""".lstrip(),
        encoding="utf-8",
    )

    (nodes_dir / "TSK-001.md").write_text(
        """
---
id: TSK-001
type: task
status: active
title: Follow-up Task
summary: Follow-up task summary.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations: []
---

Body.
""".lstrip(),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "query",
            "--path",
            str(tmp_path),
            "--id",
            "DEC-001",
            "--direction",
            "downstream",
            "--depth",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert "QUERY DEC-001 direction=downstream depth=2" in result.output
    assert "node=MOD-001" in result.output
    assert "node=TSK-001" in result.output
    assert "edge=DEC-001->MOD-001" in result.output
    assert "edge=MOD-001->TSK-001" in result.output


def test_cli_query_upstream(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_path)])
    nodes_dir = tmp_path / ".amta" / "nodes"

    (nodes_dir / "DEC-001.md").write_text(
        """
---
id: DEC-001
type: decision
status: active
title: First Decision
summary: First decision summary.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations:
  - type: impacts
    target: MOD-001
---

Body.
""".lstrip(),
        encoding="utf-8",
    )

    (nodes_dir / "MOD-001.md").write_text(
        """
---
id: MOD-001
type: module
status: active
title: Core Module
summary: Core module summary.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations: []
---

Body.
""".lstrip(),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "query",
            "--path",
            str(tmp_path),
            "--id",
            "MOD-001",
            "--direction",
            "upstream",
        ],
    )

    assert result.exit_code == 0
    assert "QUERY MOD-001 direction=upstream depth=1" in result.output
    assert "node=DEC-001" in result.output
    assert "edge=DEC-001->MOD-001" in result.output


def test_cli_query_missing_node_returns_fail(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "query",
            "--path",
            str(tmp_path),
            "--id",
            "DEC-999",
        ],
    )

    assert result.exit_code == 3
    assert "node not found: DEC-999" in result.output
