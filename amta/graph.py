"""Graph construction utilities for AMTA."""

from __future__ import annotations

from datetime import UTC, datetime

import networkx as nx

from amta.models import (
    ConfigModel,
    EdgeModel,
    GraphModel,
    NodeModel,
    NodeStatus,
    NodeType,
    StatisticsModel,
)


def build_networkx_graph(nodes: list[NodeModel]) -> nx.DiGraph[str]:
    """Build a NetworkX directed graph from validated AMTA nodes."""
    graph: nx.DiGraph[str] = nx.DiGraph()

    for node in sorted(nodes, key=lambda item: item.id):
        graph.add_node(
            node.id,
            type=node.type.value,
            status=node.status.value,
            title=node.title,
            summary=node.summary,
            owner=node.owner,
        )

    for node in sorted(nodes, key=lambda item: item.id):
        for relation in sorted(node.relations, key=lambda item: (item.type, item.target)):
            graph.add_edge(
                node.id,
                relation.target,
                relation=relation.type,
            )

    return graph


def build_edges(nodes: list[NodeModel]) -> list[EdgeModel]:
    """Build deterministic serializable edges from AMTA nodes."""
    edges: list[EdgeModel] = []

    for node in sorted(nodes, key=lambda item: item.id):
        for relation in sorted(node.relations, key=lambda item: (item.type, item.target)):
            edges.append(
                EdgeModel(
                    source=node.id,
                    target=relation.target,
                    relation=relation.type,
                )
            )

    return edges


def compute_statistics(nodes: list[NodeModel], edges: list[EdgeModel]) -> StatisticsModel:
    """Compute graph statistics."""
    return StatisticsModel(
        total_nodes=len(nodes),
        total_edges=len(edges),
        total_decisions=sum(1 for node in nodes if node.type is NodeType.DECISION),
        total_tasks=sum(1 for node in nodes if node.type is NodeType.TASK),
        total_constraints=sum(1 for node in nodes if node.type is NodeType.CONSTRAINT),
        total_incidents=sum(1 for node in nodes if node.type is NodeType.INCIDENT),
        total_modules=sum(1 for node in nodes if node.type is NodeType.MODULE),
        total_events=sum(1 for node in nodes if node.type is NodeType.EVENT),
        total_proposed=sum(1 for node in nodes if node.status is NodeStatus.PROPOSED),
        total_active=sum(1 for node in nodes if node.status is NodeStatus.ACTIVE),
        total_blocked=sum(1 for node in nodes if node.status is NodeStatus.BLOCKED),
        total_completed=sum(1 for node in nodes if node.status is NodeStatus.COMPLETED),
        total_deprecated=sum(1 for node in nodes if node.status is NodeStatus.DEPRECATED),
    )


def build_graph_model(
    nodes: list[NodeModel],
    config: ConfigModel,
    *,
    generated_at: str | None = None,
) -> GraphModel:
    """Build serializable GraphModel from AMTA nodes and config."""
    sorted_nodes = sorted(nodes, key=lambda item: item.id)
    edges = build_edges(sorted_nodes)
    statistics = compute_statistics(sorted_nodes, edges)

    timestamp = generated_at or datetime.now(UTC).replace(microsecond=0).isoformat()

    return GraphModel(
        workspace=config.workspace.id,
        namespace=config.workspace.namespace,
        generated_at=timestamp,
        statistics=statistics,
        nodes=sorted_nodes,
        edges=edges,
    )
