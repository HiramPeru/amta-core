"""Markdown node parser for AMTA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter
from pydantic import ValidationError

from amta.errors import AmtaParseError
from amta.models import NodeModel

NODES_DIRNAME = "nodes"


def parse_node_file(path: str | Path) -> NodeModel:
    """Parse one Markdown node file into NodeModel."""
    node_path = Path(path)

    if not node_path.exists():
        raise AmtaParseError(f"Node file not found: {node_path}")

    if not node_path.is_file():
        raise AmtaParseError(f"Node path is not a file: {node_path}")

    if node_path.suffix != ".md":
        raise AmtaParseError(f"Node file must use .md extension: {node_path}")

    try:
        post = frontmatter.load(node_path)
    except Exception as exc:
        raise AmtaParseError(f"Failed to parse frontmatter in {node_path}: {exc}") from exc

    metadata: dict[str, Any] = dict(post.metadata)

    if not metadata:
        raise AmtaParseError(f"Missing frontmatter in node file: {node_path}")

    metadata["body"] = post.content

    try:
        return NodeModel.model_validate(metadata)
    except ValidationError as exc:
        raise AmtaParseError(f"Invalid node metadata in {node_path}: {exc}") from exc


def parse_nodes_dir(nodes_dir: str | Path) -> list[NodeModel]:
    """Parse every Markdown node file in deterministic filename order."""
    nodes_path = Path(nodes_dir)

    if not nodes_path.exists():
        raise AmtaParseError(f"Nodes directory not found: {nodes_path}")

    if not nodes_path.is_dir():
        raise AmtaParseError(f"Nodes path is not a directory: {nodes_path}")

    node_files = sorted(nodes_path.glob("*.md"))

    return [parse_node_file(node_file) for node_file in node_files]


def parse_workspace_nodes(workspace_dir: str | Path) -> list[NodeModel]:
    """Parse .amta/nodes for a workspace directory."""
    return parse_nodes_dir(Path(workspace_dir) / NODES_DIRNAME)
