"""JSON Schema generation for AMTA public models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from amta.models import ConfigModel, GraphModel, NodeModel

SCHEMA_FILENAMES = {
    "node": "node.schema.json",
    "config": "config.schema.json",
    "graph": "graph.schema.json",
}


def get_schemas() -> dict[str, dict[str, Any]]:
    """Return JSON schemas for public AMTA models."""
    return {
        "node": NodeModel.model_json_schema(),
        "config": ConfigModel.model_json_schema(),
        "graph": GraphModel.model_json_schema(),
    }


def render_schema(schema: dict[str, Any]) -> str:
    """Render JSON schema deterministically."""
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def write_schemas(output_dir: Path) -> dict[str, Path]:
    """Write public JSON schemas into output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, Path] = {}
    for name, schema in get_schemas().items():
        path = output_dir / SCHEMA_FILENAMES[name]
        path.write_text(render_schema(schema), encoding="utf-8")
        written[name] = path

    return written
