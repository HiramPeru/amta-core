"""AMTA validation engine."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum

import networkx as nx

from amta.models import ConfigModel, NodeModel, ValidationMode


class ValidationSeverity(StrEnum):
    """Validation finding severity."""

    ERROR = "error"
    WARNING = "warning"


class ValidationStatus(StrEnum):
    """Overall validation status."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ValidationFinding:
    """Single validation finding."""

    code: str
    severity: ValidationSeverity
    message: str
    node_id: str | None = None


@dataclass
class ValidationResult:
    """Validation result."""

    status: ValidationStatus = ValidationStatus.PASS
    errors: list[ValidationFinding] = field(default_factory=list)
    warnings: list[ValidationFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return true when validation has no errors."""
        return not self.errors

    def add_error(self, code: str, message: str, node_id: str | None = None) -> None:
        """Append an error finding."""
        self.errors.append(
            ValidationFinding(
                code=code,
                severity=ValidationSeverity.ERROR,
                message=message,
                node_id=node_id,
            )
        )

    def add_warning(self, code: str, message: str, node_id: str | None = None) -> None:
        """Append a warning finding."""
        self.warnings.append(
            ValidationFinding(
                code=code,
                severity=ValidationSeverity.WARNING,
                message=message,
                node_id=node_id,
            )
        )

    def finalize(self, *, fail_on_warnings: bool = False) -> ValidationResult:
        """Compute final status."""
        if self.errors or (fail_on_warnings and self.warnings):
            self.status = ValidationStatus.FAIL
        elif self.warnings:
            self.status = ValidationStatus.WARN
        else:
            self.status = ValidationStatus.PASS

        return self


def validate_nodes(nodes: list[NodeModel], config: ConfigModel) -> ValidationResult:
    """Validate parsed nodes against workspace config."""
    result = ValidationResult()

    node_ids = [node.id for node in nodes]
    node_id_set = set(node_ids)

    _validate_unique_ids(node_ids, result)
    _validate_owners(nodes, config, result)
    _validate_relations(nodes, config, node_id_set, result)
    _validate_orphans(nodes, result)
    _validate_cycles(nodes, config, result)

    return result.finalize(fail_on_warnings=config.validation.fail_on_warnings)


def _validate_unique_ids(node_ids: list[str], result: ValidationResult) -> None:
    counts = Counter(node_ids)
    for node_id, count in sorted(counts.items()):
        if count > 1:
            result.add_error("VAL-007", f"Duplicate node id: {node_id}", node_id=node_id)


def _validate_owners(
    nodes: list[NodeModel],
    config: ConfigModel,
    result: ValidationResult,
) -> None:
    if not config.validation.enforce_owners:
        return

    owners = set(config.owners)
    for node in nodes:
        if node.owner not in owners:
            result.add_error(
                "VAL-OWNER-001",
                f"Unknown owner {node.owner!r}; expected one of {sorted(owners)!r}",
                node_id=node.id,
            )


def _validate_relations(
    nodes: list[NodeModel],
    config: ConfigModel,
    node_id_set: set[str],
    result: ValidationResult,
) -> None:
    relation_catalog = set(config.graph.relation_types)
    seen_edges: set[tuple[str, str, str]] = set()

    for node in nodes:
        for relation in node.relations:
            if relation.target == node.id:
                result.add_error(
                    "VAL-008",
                    f"Self-reference is not allowed: {node.id} -> {relation.target}",
                    node_id=node.id,
                )

            if relation.target not in node_id_set:
                result.add_error(
                    "VAL-005",
                    f"Relation target does not exist: {relation.target}",
                    node_id=node.id,
                )

            if relation.type not in relation_catalog:
                message = (
                    f"Relation type {relation.type!r} is not in catalog "
                    f"{sorted(relation_catalog)!r}"
                )
                if config.validation.relation_catalog_mode is ValidationMode.STRICT:
                    result.add_error("VAL-REL-001", message, node_id=node.id)
                else:
                    result.add_warning("VAL-REL-001", message, node_id=node.id)

            edge_key = (node.id, relation.target, relation.type)
            if edge_key in seen_edges:
                result.add_error(
                    "VAL-010",
                    f"Duplicate edge: {node.id} -[{relation.type}]-> {relation.target}",
                    node_id=node.id,
                )
            seen_edges.add(edge_key)


def _validate_orphans(nodes: list[NodeModel], result: ValidationResult) -> None:
    node_ids = {node.id for node in nodes}
    connected_ids: set[str] = set()

    for node in nodes:
        if node.relations:
            connected_ids.add(node.id)
        for relation in node.relations:
            if relation.target in node_ids:
                connected_ids.add(relation.target)

    for node_id in sorted(node_ids - connected_ids):
        result.add_warning("VAL-W001", f"Orphan node: {node_id}", node_id=node_id)


def _validate_cycles(
    nodes: list[NodeModel],
    config: ConfigModel,
    result: ValidationResult,
) -> None:
    if not config.validation.enforce_cycles:
        return

    graph: nx.DiGraph[str] = nx.DiGraph()
    for node in nodes:
        graph.add_node(node.id)
        for relation in node.relations:
            graph.add_edge(node.id, relation.target)

    try:
        cycle = nx.find_cycle(graph, orientation="original")
    except nx.NetworkXNoCycle:
        return

    cycle_path = " -> ".join(edge[0] for edge in cycle)
    result.add_error("VAL-009", f"Cycle detected: {cycle_path}")
