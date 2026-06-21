"""AMTA command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from amta.builder import build_workspace_artifacts
from amta.config import CONFIG_FILENAME, WORKSPACE_DIRNAME, find_workspace_dir, load_config
from amta.errors import AmtaConfigError, AmtaParseError
from amta.importer import AmtaImportError, import_context
from amta.parser import parse_workspace_nodes
from amta.schemas import write_schemas
from amta.validator import ValidationResult, ValidationStatus, validate_nodes

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

    build_workspace_artifacts(nodes, config, workspace_dir)
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
    """Import legacy context Markdown into AMTA nodes."""
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
