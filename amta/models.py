"""Core Pydantic models for AMTA.

Design decision:
- NodeModel.id is local to the workspace, e.g. "DEC-001".
- Workspace namespace is not stored in NodeModel.
- Fully qualified canonical IDs are generated later by the graph/export layer.
"""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NODE_ID_PATTERN = re.compile(r"^[A-Z]{3}-[0-9]{3,}$")
WORKSPACE_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
NAMESPACE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*$")


class NodeType(StrEnum):
    """Supported AMTA node types for v0.1."""

    DECISION = "decision"
    TASK = "task"
    CONSTRAINT = "constraint"
    INCIDENT = "incident"
    MODULE = "module"
    EVENT = "event"


class NodeStatus(StrEnum):
    """Supported AMTA node states for v0.1."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DEPRECATED = "deprecated"


class ValidationMode(StrEnum):
    """Validation behavior for configurable catalogs."""

    STRICT = "strict"
    LAX = "lax"


TYPE_PREFIXES: dict[NodeType, str] = {
    NodeType.DECISION: "DEC",
    NodeType.TASK: "TSK",
    NodeType.CONSTRAINT: "CON",
    NodeType.INCIDENT: "INC",
    NodeType.MODULE: "MOD",
    NodeType.EVENT: "EVT",
}


class RelationModel(BaseModel):
    """Directed relation declared by a node."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = Field(min_length=1, max_length=64)
    target: str = Field(pattern=NODE_ID_PATTERN.pattern)

    @field_validator("type")
    @classmethod
    def validate_relation_type_format(cls, value: str) -> str:
        """Validate relation type syntax without enforcing catalog membership."""
        if not re.fullmatch(r"^[a-z][a-z0-9_]*$", value):
            raise ValueError("relation type must match ^[a-z][a-z0-9_]*$")
        return value


class NodeModel(BaseModel):
    """Local AMTA node model."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=NODE_ID_PATTERN.pattern)
    type: NodeType
    status: NodeStatus
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    owner: str = Field(min_length=1, max_length=100)
    revision: int = Field(ge=1)
    created: date
    updated: date
    tags: list[str] = Field(default_factory=list)
    relations: list[RelationModel] = Field(default_factory=list)
    body: str = ""

    _type_prefixes: ClassVar[dict[NodeType, str]] = TYPE_PREFIXES

    @field_validator("owner")
    @classmethod
    def validate_owner_format(cls, value: str) -> str:
        """Validate owner syntax."""
        if not re.fullmatch(r"^[a-z][a-z0-9_-]*$", value):
            raise ValueError("owner must match ^[a-z][a-z0-9_-]*$")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        """Validate tag syntax."""
        for tag in value:
            if not re.fullmatch(r"^[a-z][a-z0-9_-]*$", tag):
                raise ValueError(f"invalid tag: {tag}")
        return value

    @model_validator(mode="after")
    def validate_dates_and_prefix(self) -> NodeModel:
        """Validate cross-field invariants."""
        if self.updated < self.created:
            raise ValueError("updated must be greater than or equal to created")

        expected_prefix = self._type_prefixes[self.type]
        actual_prefix = self.id.split("-", 1)[0]
        if actual_prefix != expected_prefix:
            raise ValueError(
                f"id prefix {actual_prefix!r} does not match type {self.type!r}; "
                f"expected {expected_prefix!r}"
            )

        return self


class WorkspaceModel(BaseModel):
    """AMTA workspace identity."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=WORKSPACE_ID_PATTERN.pattern)
    name: str = Field(min_length=1, max_length=200)
    version: int = Field(ge=1)
    namespace: str | None = Field(default=None)

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, value: str | None) -> str | None:
        """Validate optional federation namespace."""
        if value is None:
            return value
        if not NAMESPACE_PATTERN.fullmatch(value):
            raise ValueError("namespace must match ^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*$")
        return value

    def canonical_id_for(self, node_id: str) -> str:
        """Return fully qualified canonical ID for export/federation."""
        if not NODE_ID_PATTERN.fullmatch(node_id):
            raise ValueError(f"invalid node id: {node_id}")

        if self.namespace:
            return f"{self.namespace}/{self.id}:{node_id}"

        return f"{self.id}:{node_id}"


class ValidationConfigModel(BaseModel):
    """Validation configuration."""

    model_config = ConfigDict(extra="forbid")

    fail_on_warnings: bool = False
    enforce_owners: bool = True
    enforce_cycles: bool = True
    relation_catalog_mode: ValidationMode = ValidationMode.LAX


class BuildConfigModel(BaseModel):
    """Build configuration."""

    model_config = ConfigDict(extra="forbid")

    generate_graph: bool = True
    generate_manifest: bool = True
    generate_state: bool = True
    generate_roadmap: bool = True
    generate_changelog: bool = True


class GraphConfigModel(BaseModel):
    """Graph configuration and catalogs."""

    model_config = ConfigDict(extra="forbid")

    relation_types: list[str] = Field(default_factory=lambda: ["depends_on", "impacts"])

    @field_validator("relation_types")
    @classmethod
    def validate_relation_types(cls, value: list[str]) -> list[str]:
        """Validate relation type catalog."""
        if not value:
            raise ValueError("relation_types cannot be empty")

        seen: set[str] = set()
        for relation_type in value:
            if not re.fullmatch(r"^[a-z][a-z0-9_]*$", relation_type):
                raise ValueError(f"invalid relation type: {relation_type}")
            if relation_type in seen:
                raise ValueError(f"duplicate relation type: {relation_type}")
            seen.add(relation_type)

        return value


class ConfigModel(BaseModel):
    """AMTA workspace configuration."""

    model_config = ConfigDict(extra="forbid")

    workspace: WorkspaceModel
    owners: list[str]
    graph: GraphConfigModel = Field(default_factory=GraphConfigModel)
    validation: ValidationConfigModel = Field(default_factory=ValidationConfigModel)
    build: BuildConfigModel = Field(default_factory=BuildConfigModel)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("owners")
    @classmethod
    def validate_owners(cls, value: list[str]) -> list[str]:
        """Validate owner catalog."""
        if not value:
            raise ValueError("owners cannot be empty")

        seen: set[str] = set()
        for owner in value:
            if not re.fullmatch(r"^[a-z][a-z0-9_-]*$", owner):
                raise ValueError(f"invalid owner: {owner}")
            if owner in seen:
                raise ValueError(f"duplicate owner: {owner}")
            seen.add(owner)

        return value


class EdgeModel(BaseModel):
    """Serialized graph edge."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(pattern=NODE_ID_PATTERN.pattern)
    target: str = Field(pattern=NODE_ID_PATTERN.pattern)
    relation: str = Field(min_length=1, max_length=64)


class StatisticsModel(BaseModel):
    """Graph statistics."""

    model_config = ConfigDict(extra="forbid")

    total_nodes: int = 0
    total_edges: int = 0
    total_decisions: int = 0
    total_tasks: int = 0
    total_constraints: int = 0
    total_incidents: int = 0
    total_modules: int = 0
    total_events: int = 0
    total_proposed: int = 0
    total_active: int = 0
    total_blocked: int = 0
    total_completed: int = 0
    total_deprecated: int = 0


class GraphModel(BaseModel):
    """Serializable graph artifact model."""

    model_config = ConfigDict(extra="forbid")

    version: str = "1.0"
    workspace: str
    namespace: str | None = None
    generated_at: str
    statistics: StatisticsModel
    nodes: list[NodeModel]
    edges: list[EdgeModel]
