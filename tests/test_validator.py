from amta.models import ConfigModel, NodeModel, RelationModel
from amta.validator import ValidationStatus, validate_nodes


def make_config(**overrides: object) -> ConfigModel:
    data: dict[str, object] = {
        "workspace": {
            "id": "amta-core",
            "name": "AMTA Core",
            "version": 1,
            "namespace": "hiram",
        },
        "owners": ["architecture", "product"],
    }
    data.update(overrides)
    return ConfigModel.model_validate(data)


def make_node(
    node_id: str,
    node_type: str,
    *,
    owner: str = "architecture",
    relations: list[RelationModel] | None = None,
) -> NodeModel:
    return NodeModel(
        id=node_id,
        type=node_type,
        status="active",
        title=f"Node {node_id}",
        summary=f"Summary for {node_id}",
        owner=owner,
        revision=1,
        created="2026-06-21",
        updated="2026-06-21",
        tags=[],
        relations=relations or [],
        body="",
    )


def test_validate_nodes_passes_connected_graph() -> None:
    nodes = [
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="impacts", target="MOD-001")],
        ),
        make_node("MOD-001", "module"),
    ]

    result = validate_nodes(nodes, make_config())

    assert result.status is ValidationStatus.PASS
    assert result.errors == []
    assert result.warnings == []


def test_validate_nodes_warns_for_orphan() -> None:
    nodes = [make_node("DEC-001", "decision")]

    result = validate_nodes(nodes, make_config())

    assert result.status is ValidationStatus.WARN
    assert result.errors == []
    assert result.warnings[0].code == "VAL-W001"


def test_validate_nodes_fails_on_duplicate_ids() -> None:
    nodes = [
        make_node("DEC-001", "decision"),
        make_node("DEC-001", "decision"),
    ]

    result = validate_nodes(nodes, make_config())

    assert result.status is ValidationStatus.FAIL
    assert any(error.code == "VAL-007" for error in result.errors)


def test_validate_nodes_fails_on_unknown_owner() -> None:
    nodes = [make_node("DEC-001", "decision", owner="unknown")]

    result = validate_nodes(nodes, make_config())

    assert result.status is ValidationStatus.FAIL
    assert any(error.code == "VAL-OWNER-001" for error in result.errors)


def test_validate_nodes_fails_on_missing_relation_target() -> None:
    nodes = [
        make_node(
            "TSK-001",
            "task",
            relations=[RelationModel(type="depends_on", target="DEC-001")],
        )
    ]

    result = validate_nodes(nodes, make_config())

    assert result.status is ValidationStatus.FAIL
    assert any(error.code == "VAL-005" for error in result.errors)


def test_validate_nodes_fails_on_self_reference() -> None:
    nodes = [
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="depends_on", target="DEC-001")],
        )
    ]

    result = validate_nodes(nodes, make_config())

    assert result.status is ValidationStatus.FAIL
    assert any(error.code == "VAL-008" for error in result.errors)


def test_validate_nodes_warns_on_uncataloged_relation_in_lax_mode() -> None:
    nodes = [
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="relates_to", target="MOD-001")],
        ),
        make_node("MOD-001", "module"),
    ]

    result = validate_nodes(nodes, make_config())

    assert result.status is ValidationStatus.WARN
    assert any(warning.code == "VAL-REL-001" for warning in result.warnings)


def test_validate_nodes_fails_on_uncataloged_relation_in_strict_mode() -> None:
    nodes = [
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="relates_to", target="MOD-001")],
        ),
        make_node("MOD-001", "module"),
    ]
    config = make_config(validation={"relation_catalog_mode": "strict"})

    result = validate_nodes(nodes, config)

    assert result.status is ValidationStatus.FAIL
    assert any(error.code == "VAL-REL-001" for error in result.errors)


def test_validate_nodes_fails_on_duplicate_edge() -> None:
    nodes = [
        make_node(
            "DEC-001",
            "decision",
            relations=[
                RelationModel(type="impacts", target="MOD-001"),
                RelationModel(type="impacts", target="MOD-001"),
            ],
        ),
        make_node("MOD-001", "module"),
    ]

    result = validate_nodes(nodes, make_config())

    assert result.status is ValidationStatus.FAIL
    assert any(error.code == "VAL-010" for error in result.errors)


def test_validate_nodes_fails_on_cycle() -> None:
    nodes = [
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="impacts", target="MOD-001")],
        ),
        make_node(
            "MOD-001",
            "module",
            relations=[RelationModel(type="depends_on", target="DEC-001")],
        ),
    ]

    result = validate_nodes(nodes, make_config())

    assert result.status is ValidationStatus.FAIL
    assert any(error.code == "VAL-009" for error in result.errors)


def test_validate_nodes_can_disable_cycle_enforcement() -> None:
    nodes = [
        make_node(
            "DEC-001",
            "decision",
            relations=[RelationModel(type="impacts", target="MOD-001")],
        ),
        make_node(
            "MOD-001",
            "module",
            relations=[RelationModel(type="depends_on", target="DEC-001")],
        ),
    ]
    config = make_config(validation={"enforce_cycles": False})

    result = validate_nodes(nodes, config)

    assert result.status is ValidationStatus.PASS
    assert result.errors == []
