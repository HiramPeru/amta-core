import networkx as nx

from amta.graph import build_edges, build_graph_model, build_networkx_graph, compute_statistics
from amta.models import ConfigModel, NodeModel, RelationModel


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


def test_build_networkx_graph() -> None:
    nodes = [
        make_node("MOD-001", "module"),
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="impacts", target="MOD-001")],
        ),
    ]

    graph = build_networkx_graph(nodes)

    assert isinstance(graph, nx.DiGraph)
    assert sorted(graph.nodes) == ["DEC-001", "MOD-001"]
    assert list(graph.edges(data=True)) == [("DEC-001", "MOD-001", {"relation": "impacts"})]
    assert graph.nodes["DEC-001"]["type"] == "decision"


def test_build_edges_is_deterministic() -> None:
    nodes = [
        make_node(
            "TSK-002",
            "task",
            relations=[RelationModel(type="depends_on", target="DEC-001")],
        ),
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="impacts", target="MOD-001")],
        ),
        make_node("MOD-001", "module"),
    ]

    edges = build_edges(nodes)

    assert [(edge.source, edge.target, edge.relation) for edge in edges] == [
        ("DEC-001", "MOD-001", "impacts"),
        ("TSK-002", "DEC-001", "depends_on"),
    ]


def test_compute_statistics() -> None:
    nodes = [
        make_node("DEC-001", "decision"),
        make_node("TSK-001", "task", status="completed"),
        make_node("CON-001", "constraint", status="blocked"),
        make_node("INC-001", "incident", status="deprecated"),
        make_node("MOD-001", "module"),
        make_node("EVT-001", "event", status="completed"),
    ]
    edges = [
        RelationModel(type="impacts", target="MOD-001"),
    ]

    serial_edges = build_edges(
        [
            make_node(
                "DEC-001",
                "decision",
                relations=[RelationModel(type="impacts", target="MOD-001")],
            ),
            make_node("MOD-001", "module"),
        ]
    )
    stats = compute_statistics(nodes, serial_edges)

    assert len(edges) == 1
    assert stats.total_nodes == 6
    assert stats.total_edges == 1
    assert stats.total_decisions == 1
    assert stats.total_tasks == 1
    assert stats.total_constraints == 1
    assert stats.total_incidents == 1
    assert stats.total_modules == 1
    assert stats.total_events == 1
    assert stats.total_active == 2
    assert stats.total_completed == 2
    assert stats.total_blocked == 1
    assert stats.total_deprecated == 1


def test_build_graph_model_is_serializable_and_deterministic() -> None:
    nodes = [
        make_node("MOD-001", "module"),
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="impacts", target="MOD-001")],
        ),
    ]

    graph_model = build_graph_model(
        nodes,
        make_config(),
        generated_at="2026-06-21T00:00:00+00:00",
    )

    payload = graph_model.model_dump(mode="json")

    assert payload["workspace"] == "amta-core"
    assert payload["namespace"] == "hiram"
    assert payload["generated_at"] == "2026-06-21T00:00:00+00:00"
    assert [node["id"] for node in payload["nodes"]] == ["DEC-001", "MOD-001"]
    assert payload["edges"] == [
        {
            "source": "DEC-001",
            "target": "MOD-001",
            "relation": "impacts",
        }
    ]
    assert payload["statistics"]["total_nodes"] == 2
    assert payload["statistics"]["total_edges"] == 1
