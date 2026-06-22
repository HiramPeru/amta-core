"""Artifact builders for AMTA."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from amta.graph import build_graph_model
from amta.models import ConfigModel, GraphModel, NodeModel, NodeStatus, NodeType
from amta.validator import ValidationStatus

GENERATED_DIRNAME = "generated"


def _resolve_generated_at(nodes: list[NodeModel], generated_at: str | None) -> str:
    """Resolve a deterministic artifact timestamp.

    When generated_at is not provided, AMTA derives the timestamp from the
    latest node updated date to preserve reproducible builds. The derived
    value is an artifact timestamp, not necessarily the real execution time.
    """
    if generated_at is not None:
        return generated_at

    updated_dates = sorted(node.updated.isoformat() for node in nodes)
    if not updated_dates:
        return "1970-01-01T00:00:00+00:00"

    return f"{updated_dates[-1]}T00:00:00+00:00"


def build_workspace_artifacts(
    nodes: list[NodeModel],
    config: ConfigModel,
    workspace_dir: str | Path,
    *,
    generated_at: str | None = None,
    validation_status: ValidationStatus = ValidationStatus.PASS,
) -> GraphModel:
    """Build all enabled workspace artifacts."""
    timestamp = _resolve_generated_at(nodes, generated_at)
    graph_model = build_graph_model(nodes, config, generated_at=timestamp)

    output_dir = Path(workspace_dir) / GENERATED_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[str] = []

    if config.build.generate_graph:
        _write_text(output_dir / "GRAPH.json", render_graph_json(graph_model))
        artifacts.append("GRAPH.json")

    if config.build.generate_state:
        _write_text(
            output_dir / "STATE.md",
            render_state_md(graph_model, validation_status=validation_status),
        )
        artifacts.append("STATE.md")

    if config.build.generate_roadmap:
        _write_text(output_dir / "ROADMAP.md", render_roadmap_md(graph_model))
        artifacts.append("ROADMAP.md")

    if config.build.generate_changelog:
        _write_text(output_dir / "CHANGELOG.md", render_changelog_md(graph_model))
        artifacts.append("CHANGELOG.md")

    if config.build.generate_manifest:
        _write_text(
            output_dir / "MANIFEST.json",
            render_manifest_json(
                version=graph_model.version,
                workspace=graph_model.workspace,
                namespace=graph_model.namespace,
                generated_at=timestamp,
                artifacts=artifacts,
            ),
        )

    return graph_model


def render_graph_json(graph_model: GraphModel) -> str:
    """Render GRAPH.json."""
    return json.dumps(graph_model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def render_manifest_json(
    *,
    version: str,
    workspace: str,
    namespace: str | None,
    generated_at: str,
    artifacts: list[str],
) -> str:
    """Render MANIFEST.json."""
    payload: dict[str, Any] = {
        "version": version,
        "workspace": workspace,
        "namespace": namespace,
        "generated_at": generated_at,
        "artifacts": sorted(artifacts),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_state_md(
    graph_model: GraphModel,
    *,
    validation_status: ValidationStatus = ValidationStatus.PASS,
) -> str:
    """Render STATE.md."""
    stats = graph_model.statistics
    return "\n".join(
        [
            "# STATE",
            "",
            f"Generated at: `{graph_model.generated_at}`",
            "",
            "## Workspace",
            "",
            f"- Workspace: `{graph_model.workspace}`",
            f"- Namespace: `{graph_model.namespace or ''}`",
            "",
            "## Graph Health",
            "",
            f"- Status: `{validation_status.value}`",
            "",
            "## Statistics",
            "",
            f"- Nodes: {stats.total_nodes}",
            f"- Edges: {stats.total_edges}",
            f"- Decisions: {stats.total_decisions}",
            f"- Tasks: {stats.total_tasks}",
            f"- Constraints: {stats.total_constraints}",
            f"- Incidents: {stats.total_incidents}",
            f"- Modules: {stats.total_modules}",
            f"- Events: {stats.total_events}",
            "",
            "## Status Counts",
            "",
            f"- Proposed: {stats.total_proposed}",
            f"- Active: {stats.total_active}",
            f"- Blocked: {stats.total_blocked}",
            f"- Completed: {stats.total_completed}",
            f"- Deprecated: {stats.total_deprecated}",
            "",
        ]
    )


def render_roadmap_md(graph_model: GraphModel) -> str:
    """Render ROADMAP.md from non-completed task nodes."""
    roadmap_nodes = [
        node
        for node in graph_model.nodes
        if node.type is NodeType.TASK and node.status is not NodeStatus.COMPLETED
    ]

    grouped: dict[NodeStatus, list[NodeModel]] = {
        NodeStatus.BLOCKED: [],
        NodeStatus.ACTIVE: [],
        NodeStatus.PROPOSED: [],
        NodeStatus.DEPRECATED: [],
    }

    for node in roadmap_nodes:
        grouped.setdefault(node.status, []).append(node)

    lines = [
        "# ROADMAP",
        "",
        f"Generated at: `{graph_model.generated_at}`",
        "",
    ]

    for status in [
        NodeStatus.BLOCKED,
        NodeStatus.ACTIVE,
        NodeStatus.PROPOSED,
        NodeStatus.DEPRECATED,
    ]:
        nodes = sorted(grouped.get(status, []), key=lambda item: item.id)
        lines.extend([f"## {status.value.title()}", ""])
        if nodes:
            for node in nodes:
                lines.append(f"- `{node.id}` — {node.title}")
        else:
            lines.append("_No items._")
        lines.append("")

    return "\n".join(lines)


def render_changelog_md(graph_model: GraphModel) -> str:
    """Render CHANGELOG.md from event nodes."""
    events = sorted(
        [node for node in graph_model.nodes if node.type is NodeType.EVENT],
        key=lambda item: (item.updated, item.id),
        reverse=True,
    )

    lines = [
        "# CHANGELOG",
        "",
        f"Generated at: `{graph_model.generated_at}`",
        "",
    ]

    if not events:
        lines.append("_No events._")
        lines.append("")
        return "\n".join(lines)

    current_date: str | None = None
    for event in events:
        event_date = event.updated.isoformat()
        if event_date != current_date:
            if current_date is not None:
                lines.append("")
            lines.extend([f"## {event_date}", ""])
            current_date = event_date
        lines.append(f"- `{event.id}` — {event.title}")

    lines.append("")
    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
