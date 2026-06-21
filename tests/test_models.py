from pydantic import ValidationError

from amta.models import (
    ConfigModel,
    NodeModel,
    NodeType,
    RelationModel,
    ValidationMode,
    WorkspaceModel,
)


def test_node_minimal() -> None:
    node = NodeModel(
        id="DEC-001",
        type="decision",
        status="active",
        title="Test",
        summary="A test decision",
        owner="architecture",
        revision=1,
        created="2026-06-21",
        updated="2026-06-21",
        tags=[],
        relations=[],
        body="# Test\n\nBody.",
    )

    assert node.id == "DEC-001"
    assert node.type is NodeType.DECISION
    assert node.body == "# Test\n\nBody."


def test_node_rejects_wrong_prefix_for_type() -> None:
    try:
        NodeModel(
            id="DEC-001",
            type="task",
            status="active",
            title="Test",
            summary="A test task",
            owner="architecture",
            revision=1,
            created="2026-06-21",
            updated="2026-06-21",
            tags=[],
            relations=[],
            body="",
        )
    except ValidationError as exc:
        assert "does not match type" in str(exc)
    else:
        raise AssertionError("expected ValidationError")


def test_node_accepts_relations() -> None:
    node = NodeModel(
        id="TSK-001",
        type="task",
        status="active",
        title="Implement models",
        summary="Implement the first Pydantic models",
        owner="architecture",
        revision=1,
        created="2026-06-21",
        updated="2026-06-21",
        tags=["architecture"],
        relations=[
            RelationModel(type="depends_on", target="DEC-001"),
            RelationModel(type="impacts", target="MOD-001"),
        ],
        body="",
    )

    assert len(node.relations) == 2
    assert node.relations[0].type == "depends_on"
    assert node.relations[0].target == "DEC-001"


def test_workspace_canonical_id_without_namespace() -> None:
    workspace = WorkspaceModel(id="menu-togo", name="Menu To Go", version=1)

    assert workspace.canonical_id_for("DEC-001") == "menu-togo:DEC-001"


def test_workspace_canonical_id_with_namespace() -> None:
    workspace = WorkspaceModel(
        id="menu-togo",
        name="Menu To Go",
        version=1,
        namespace="hiram",
    )

    assert workspace.canonical_id_for("DEC-001") == "hiram/menu-togo:DEC-001"


def test_config_relation_catalog_lax_by_default() -> None:
    config = ConfigModel(
        workspace={
            "id": "amta-core",
            "name": "AMTA Core",
            "version": 1,
            "namespace": "hiram",
        },
        owners=["architecture", "product"],
    )

    assert config.graph.relation_types == ["depends_on", "impacts"]
    assert config.validation.relation_catalog_mode is ValidationMode.LAX
