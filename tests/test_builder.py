import json
from pathlib import Path

from amta.builder import (
    build_workspace_artifacts,
    render_changelog_md,
    render_graph_json,
    render_manifest_json,
    render_roadmap_md,
    render_state_md,
)
from amta.graph import build_graph_model
from amta.models import ConfigModel, NodeModel, RelationModel
from amta.validator import ValidationStatus


def make_config() -> ConfigModel:
    return ConfigModel(
        workspace={
            "id": "amta-core",
            "name": "AMTA Core",
            "version": 1,
            "namespace": "hiram",
        },
        owners=["architecture"],
    )


def make_node(
    node_id: str,
    node_type: str,
    *,
    status: str = "active",
    relations: list[RelationModel] | None = None,
) -> NodeModel:
    return NodeModel(
        id=node_id,
        type=node_type,
        status=status,
        title=f"Node {node_id}",
        summary=f"Summary for {node_id}",
        owner="architecture",
        revision=1,
        created="2026-06-21",
        updated="2026-06-21",
        tags=[],
        relations=relations or [],
        body="",
    )


def test_render_graph_json() -> None:
    graph_model = build_graph_model(
        [
            make_node(
                "DEC-001",
                "decision",
                relations=[RelationModel(type="impacts", target="MOD-001")],
            ),
            make_node("MOD-001", "module"),
        ],
        make_config(),
        generated_at="2026-06-21T00:00:00+00:00",
    )

    payload = json.loads(render_graph_json(graph_model))

    assert payload["workspace"] == "amta-core"
    assert payload["namespace"] == "hiram"
    assert payload["edges"] == [
        {
            "relation": "impacts",
            "source": "DEC-001",
            "target": "MOD-001",
        }
    ]


def test_render_manifest_json_sorts_artifacts() -> None:
    payload = json.loads(
        render_manifest_json(
            version="1.0",
            workspace="amta-core",
            namespace="hiram",
            generated_at="2026-06-21T00:00:00+00:00",
            artifacts=["STATE.md", "GRAPH.json"],
        )
    )

    assert payload["artifacts"] == ["GRAPH.json", "STATE.md"]


def test_render_state_md() -> None:
    graph_model = build_graph_model(
        [make_node("DEC-001", "decision")],
        make_config(),
        generated_at="2026-06-21T00:00:00+00:00",
    )

    content = render_state_md(graph_model)

    assert "# STATE" in content
    assert "- Workspace: `amta-core`" in content
    assert "- Status: `PASS`" in content
    assert "- Nodes: 1" in content


def test_render_state_md_with_warn_status() -> None:
    graph_model = build_graph_model(
        [make_node("DEC-001", "decision")],
        make_config(),
        generated_at="2026-06-21T00:00:00+00:00",
    )

    content = render_state_md(graph_model, validation_status=ValidationStatus.WARN)

    assert "- Status: `WARN`" in content


def test_render_state_md_with_fail_status() -> None:
    graph_model = build_graph_model(
        [make_node("DEC-001", "decision")],
        make_config(),
        generated_at="2026-06-21T00:00:00+00:00",
    )

    content = render_state_md(graph_model, validation_status=ValidationStatus.FAIL)

    assert "- Status: `FAIL`" in content


def test_render_roadmap_md_only_non_completed_tasks() -> None:
    graph_model = build_graph_model(
        [
            make_node("TSK-001", "task", status="active"),
            make_node("TSK-002", "task", status="completed"),
            make_node("DEC-001", "decision"),
        ],
        make_config(),
        generated_at="2026-06-21T00:00:00+00:00",
    )

    content = render_roadmap_md(graph_model)

    assert "`TSK-001`" in content
    assert "`TSK-002`" not in content
    assert "`DEC-001`" not in content


def test_render_changelog_md_from_events() -> None:
    graph_model = build_graph_model(
        [
            make_node("EVT-001", "event", status="completed"),
            make_node("DEC-001", "decision"),
        ],
        make_config(),
        generated_at="2026-06-21T00:00:00+00:00",
    )

    content = render_changelog_md(graph_model)

    assert "# CHANGELOG" in content
    assert "## 2026-06-21" in content
    assert "`EVT-001`" in content
    assert "`DEC-001`" not in content


def test_build_workspace_artifacts(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".amta"
    nodes = [
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="impacts", target="MOD-001")],
        ),
        make_node("MOD-001", "module"),
        make_node("EVT-001", "event", status="completed"),
        make_node("TSK-001", "task", status="active"),
    ]

    graph_model = build_workspace_artifacts(
        nodes,
        make_config(),
        workspace_dir,
        generated_at="2026-06-21T00:00:00+00:00",
    )

    generated_dir = workspace_dir / "generated"

    assert graph_model.statistics.total_nodes == 4
    assert (generated_dir / "GRAPH.json").exists()
    assert (generated_dir / "MANIFEST.json").exists()
    assert (generated_dir / "STATE.md").exists()
    assert (generated_dir / "ROADMAP.md").exists()
    assert (generated_dir / "CHANGELOG.md").exists()

    manifest = json.loads((generated_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["artifacts"] == ["CHANGELOG.md", "GRAPH.json", "ROADMAP.md", "STATE.md"]
