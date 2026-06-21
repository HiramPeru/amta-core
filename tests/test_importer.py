from __future__ import annotations

from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from amta.cli import app
from amta.importer import import_context
from amta.parser import parse_nodes_dir

runner = CliRunner()


def test_import_context_writes_valid_nodes(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    context_dir.mkdir()
    source_file = context_dir / "decision-log.md"
    source_file.write_text(
        "# Keep Ledger Atomic\n\nPayments must be registered atomically.\n",
        encoding="utf-8",
    )

    result = import_context(tmp_path, import_date=date(2026, 6, 21))

    assert len(result.imported_nodes) == 1
    assert result.imported_nodes[0].node_id == "DEC-001"

    nodes = parse_nodes_dir(tmp_path / ".amta" / "nodes")
    assert len(nodes) == 1
    assert nodes[0].id == "DEC-001"
    assert nodes[0].type == "decision"
    assert nodes[0].owner == "architecture"
    assert nodes[0].title == "Keep Ledger Atomic"
    assert "Imported from: `context/decision-log.md`" in nodes[0].body


def test_import_context_reads_data_docs(tmp_path: Path) -> None:
    docs_dir = tmp_path / "Data" / "Docs"
    docs_dir.mkdir(parents=True)
    source_file = docs_dir / "SECURITY.md"
    source_file.write_text(
        "# RLS Boundary\n\nService role must not run in frontend code.\n",
        encoding="utf-8",
    )

    result = import_context(tmp_path, import_date=date(2026, 6, 21))

    assert len(result.imported_nodes) == 1
    assert result.imported_nodes[0].node_id == "CON-001"

    nodes = parse_nodes_dir(tmp_path / ".amta" / "nodes")
    assert nodes[0].type == "constraint"
    assert "data-docs" in nodes[0].tags


def test_import_context_skips_existing_imported_source(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    context_dir.mkdir()
    source_file = context_dir / "incident.md"
    source_file.write_text("# Print Incident\n\nPrint layout failed.\n", encoding="utf-8")

    first = import_context(tmp_path, import_date=date(2026, 6, 21))
    second = import_context(tmp_path, import_date=date(2026, 6, 21))

    assert len(first.imported_nodes) == 1
    assert second.imported_nodes == []
    assert [warning.code for warning in second.warnings] == ["IMP-W002"]

    nodes = parse_nodes_dir(tmp_path / ".amta" / "nodes")
    assert len(nodes) == 1


def test_import_context_cli_command(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    context_dir.mkdir()
    source_file = context_dir / "module.md"
    source_file.write_text("# CRM Module\n\nCRM context document.\n", encoding="utf-8")

    result = runner.invoke(app, ["import-context", "--path", str(tmp_path)])

    assert result.exit_code == 0
    assert "PASS: imported 1 node(s)" in result.stdout
    assert (tmp_path / ".amta" / "nodes" / "MOD-001.md").exists()
