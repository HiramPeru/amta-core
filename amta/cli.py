"""AMTA command-line interface."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from amta.builder import build_workspace_artifacts
from amta.config import CONFIG_FILENAME, WORKSPACE_DIRNAME, find_workspace_dir, load_config
from amta.errors import AmtaConfigError, AmtaParseError
from amta.graph import build_graph_model
from amta.importer import AmtaImportError, import_context
from amta.models import GraphModel, NodeModel
from amta.parser import parse_workspace_nodes
from amta.schemas import write_schemas
from amta.validator import ValidationResult, ValidationStatus, validate_nodes


class QueryDirection(StrEnum):
    """Supported graph query traversal directions."""

    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"
    BOTH = "both"


app = typer.Typer(
    name="amta",
    help="AMTA Core CLI.",
    no_args_is_help=True,
)


@app.command()
def init(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Repository path where .amta will be created."),
    ] = Path("."),
    workspace_id: Annotated[
        str,
        typer.Option("--workspace-id", help="Workspace id."),
    ] = "amta-workspace",
    workspace_name: Annotated[
        str,
        typer.Option("--workspace-name", help="Workspace display name."),
    ] = "AMTA Workspace",
    namespace: Annotated[
        str | None,
        typer.Option("--namespace", help="Optional federation namespace."),
    ] = None,
) -> None:
    """Initialize an AMTA workspace."""
    root = path.resolve()
    workspace_dir = root / WORKSPACE_DIRNAME

    if workspace_dir.exists():
        typer.echo(f"FAIL: workspace already exists: {workspace_dir}", err=True)
        raise typer.Exit(code=1)

    (workspace_dir / "nodes").mkdir(parents=True)
    (workspace_dir / "generated").mkdir()
    (workspace_dir / "cache").mkdir()

    namespace_line = f"  namespace: {namespace}\n" if namespace else ""

    config_content = (
        "workspace:\n"
        f"  id: {workspace_id}\n"
        f"  name: {workspace_name}\n"
        "  version: 1\n"
        f"{namespace_line}"
        "owners:\n"
        "  - architecture\n"
        "graph:\n"
        "  relation_types:\n"
        "    - depends_on\n"
        "    - impacts\n"
        "validation:\n"
        "  fail_on_warnings: false\n"
        "  enforce_owners: true\n"
        "  enforce_cycles: true\n"
        "  relation_catalog_mode: lax\n"
        "build:\n"
        "  generate_graph: true\n"
        "  generate_manifest: true\n"
        "  generate_state: true\n"
        "  generate_roadmap: true\n"
        "  generate_changelog: true\n"
        "metadata:\n"
        "  created_by: amta init\n"
    )

    (workspace_dir / CONFIG_FILENAME).write_text(config_content, encoding="utf-8")

    typer.echo(f"PASS: initialized workspace at {workspace_dir}")


@app.command()
def validate(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path inside an AMTA workspace."),
    ] = Path("."),
) -> None:
    """Validate an AMTA workspace."""
    try:
        workspace_dir = find_workspace_dir(path)
        config = load_config(workspace_dir)
        nodes = parse_workspace_nodes(workspace_dir)
        result = validate_nodes(nodes, config)
    except (AmtaConfigError, AmtaParseError) as exc:
        typer.echo(f"FAIL: {exc}", err=True)
        raise typer.Exit(code=3) from exc

    _print_validation_result(result)

    if result.status is ValidationStatus.FAIL:
        raise typer.Exit(code=3)

    if result.status is ValidationStatus.WARN:
        raise typer.Exit(code=2)


@app.command()
def build(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path inside an AMTA workspace."),
    ] = Path("."),
) -> None:
    """Build generated AMTA artifacts."""
    try:
        workspace_dir = find_workspace_dir(path)
        config = load_config(workspace_dir)
        nodes = parse_workspace_nodes(workspace_dir)
        result = validate_nodes(nodes, config)
    except (AmtaConfigError, AmtaParseError) as exc:
        typer.echo(f"FAIL: {exc}", err=True)
        raise typer.Exit(code=3) from exc

    _print_validation_result(result)

    if result.status is ValidationStatus.FAIL:
        raise typer.Exit(code=3)

    if result.status is ValidationStatus.WARN and config.validation.fail_on_warnings:
        raise typer.Exit(code=3)

    build_workspace_artifacts(
        nodes,
        config,
        workspace_dir,
        validation_status=result.status,
    )
    typer.echo(f"PASS: generated artifacts in {workspace_dir / 'generated'}")


@app.command("import-context")
def import_context_command(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Repository path to import from."),
    ] = Path("."),
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Rewrite previously imported nodes."),
    ] = False,
) -> None:
    """Import legacy context Markdown into AMTA nodes.

    This is a best-effort operation. AMTA infers node types from file names,
    paths, and content heuristics. Imported nodes must be reviewed before
    being treated as authoritative project knowledge.
    """
    try:
        result = import_context(path, overwrite=overwrite)
    except AmtaImportError as exc:
        typer.echo(f"FAIL: {exc}", err=True)
        raise typer.Exit(code=3) from exc

    for warning in result.warnings:
        suffix = f" [{warning.source_path}]" if warning.source_path else ""
        typer.echo(f"WARN {warning.code}{suffix}: {warning.message}")

    for imported_node in result.imported_nodes:
        typer.echo(
            "PASS: imported "
            f"{imported_node.source_path} -> {imported_node.node_path}"
        )

    typer.echo(f"PASS: imported {len(result.imported_nodes)} node(s)")



@app.command("query")
def query_command(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path inside an AMTA workspace."),
    ] = Path("."),
    node_id: Annotated[
        str,
        typer.Option("--id", help="Node id to query."),
    ] = "",
    direction: Annotated[
        QueryDirection,
        typer.Option("--direction", "-d", help="Traversal direction."),
    ] = QueryDirection.BOTH,
    depth: Annotated[
        int,
        typer.Option("--depth", help="Traversal depth.", min=1),
    ] = 1,
) -> None:
    """Query AMTA graph relationships."""
    if not node_id:
        typer.echo("FAIL: --id is required", err=True)
        raise typer.Exit(code=3)

    try:
        workspace_dir = find_workspace_dir(path)
        config = load_config(workspace_dir)
        nodes = parse_workspace_nodes(workspace_dir)
        result = validate_nodes(nodes, config)
    except (AmtaConfigError, AmtaParseError) as exc:
        typer.echo(f"FAIL: {exc}", err=True)
        raise typer.Exit(code=3) from exc

    if result.status is ValidationStatus.FAIL:
        _print_validation_result(result)
        raise typer.Exit(code=3)

    graph_model = build_graph_model(nodes, config)
    nodes_by_id = {node.id: node for node in graph_model.nodes}

    if node_id not in nodes_by_id:
        typer.echo(f"FAIL: node not found: {node_id}", err=True)
        raise typer.Exit(code=3)

    rows = _query_related_nodes(
        graph_model,
        node_id=node_id,
        direction=direction,
        depth=depth,
    )

    typer.echo(f"QUERY {node_id} direction={direction.value} depth={depth}")

    if not rows:
        typer.echo("_No related nodes._")
        return

    for distance, row_direction, relation, source_id, target_id, related_node in rows:
        typer.echo(
            f"- depth={distance} "
            f"direction={row_direction} "
            f"relation={relation} "
            f"edge={source_id}->{target_id} "
            f"node={related_node.id} "
            f"type={related_node.type.value} "
            f"status={related_node.status.value} "
            f"title={related_node.title}"
        )



@app.command("schemas")
def schemas_command(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Directory where JSON schemas will be written."),
    ] = Path("schemas"),
) -> None:
    """Generate public AMTA JSON schemas."""
    written = write_schemas(output)
    for path in written.values():
        typer.echo(f"PASS: wrote {path}")



def _query_related_nodes(
    graph_model: GraphModel,
    *,
    node_id: str,
    direction: QueryDirection,
    depth: int,
) -> list[tuple[int, str, str, str, str, NodeModel]]:
    nodes_by_id = {node.id: node for node in graph_model.nodes}

    outgoing: dict[str, list[tuple[str, str, str]]] = {}
    incoming: dict[str, list[tuple[str, str, str]]] = {}

    for edge in sorted(
        graph_model.edges,
        key=lambda item: (item.source, item.relation, item.target),
    ):
        outgoing.setdefault(edge.source, []).append((edge.relation, edge.source, edge.target))
        incoming.setdefault(edge.target, []).append((edge.relation, edge.source, edge.target))

    rows: list[tuple[int, str, str, str, str, NodeModel]] = []
    seen: set[tuple[str, str]] = set()
    frontier: list[str] = [node_id]

    for distance in range(1, depth + 1):
        next_frontier: list[str] = []

        for current_id in sorted(frontier):
            if direction in {QueryDirection.DOWNSTREAM, QueryDirection.BOTH}:
                for relation, source_id, target_id in outgoing.get(current_id, []):
                    key = ("downstream", target_id)
                    if key not in seen and target_id in nodes_by_id:
                        seen.add(key)
                        next_frontier.append(target_id)
                        rows.append(
                            (
                                distance,
                                "downstream",
                                relation,
                                source_id,
                                target_id,
                                nodes_by_id[target_id],
                            )
                        )

            if direction in {QueryDirection.UPSTREAM, QueryDirection.BOTH}:
                for relation, source_id, target_id in incoming.get(current_id, []):
                    key = ("upstream", source_id)
                    if key not in seen and source_id in nodes_by_id:
                        seen.add(key)
                        next_frontier.append(source_id)
                        rows.append(
                            (
                                distance,
                                "upstream",
                                relation,
                                source_id,
                                target_id,
                                nodes_by_id[source_id],
                            )
                        )

        frontier = sorted(set(next_frontier))

    return sorted(
        rows,
        key=lambda item: (
            item[0],
            item[1],
            item[5].id,
            item[2],
            item[3],
            item[4],
        ),
    )


def _print_validation_result(result: ValidationResult) -> None:
    status = result.status.value
    typer.echo(status)

    for warning in result.warnings:
        suffix = f" [{warning.node_id}]" if warning.node_id else ""
        typer.echo(f"WARN {warning.code}{suffix}: {warning.message}")

    for error in result.errors:
        suffix = f" [{error.node_id}]" if error.node_id else ""
        typer.echo(f"ERROR {error.code}{suffix}: {error.message}", err=True)


if __name__ == "__main__":
    app()
