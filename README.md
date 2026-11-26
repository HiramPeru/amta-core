# AMTA Core

**Project Status:** Active Python 3.12 CLI and governance library (MIT License; 59 automated pytest tests, 91% line coverage, passing GitHub Actions CI).

AMTA Core is a reusable governance engine for Markdown-based project memory.

It turns structured Markdown nodes into validated graph artifacts, generated project views, and JSON schemas for humans, agents, editors, and CI systems.

## Problem and Context

AI-assisted and multi-agent software workflows frequently lose architectural context across sessions or suffer from drifted, unstructured Markdown notes. AMTA Core enforces a deterministic, Git-native contract over project memory nodes (`CON`, `DEC`, `MOD`, `TSK`, `ADR`, `INC`) so every decision, constraint, and task is schema-validated, graph-checked, and compiled into reproducible views.

## My Role / Contribution

I designed and implemented the `amta-core` Python package, CLI (`amta`), Pydantic v2 domain models, graph integrity validator, deterministic artifact builder, JSON Schema exporter, and automated test and CI quality gates.

## What AMTA does

AMTA provides:

- structured Markdown nodes with YAML frontmatter
- Pydantic model validation
- graph integrity validation
- deterministic generated artifacts
- JSON graph export
- manifest generation
- roadmap, state, and changelog generation
- JSON Schema export for external tooling

## Architecture and Implementation

1. **Parser (`amta/parser.py`):** Reads Markdown nodes with YAML frontmatter from `.amta/nodes/`.
2. **Domain Models (`amta/models.py`, `amta/config.py`):** Enforces strict schema rules and node metadata via Pydantic v2.
3. **Graph & Validator (`amta/graph.py`, `amta/validator.py`):** Verifies unique node IDs, relation targets, self-references, duplicate edges, directed acyclic graph (DAG) cycle rules, configured owners, and orphan nodes.
4. **Deterministic Builder (`amta/builder.py`):** Emits reproducible `.amta/generated/` artifacts (`GRAPH.json`, `MANIFEST.json`, `ROADMAP.md`, `STATE.md`, `CHANGELOG.md`).
5. **Schema Exporter (`amta/schemas.py`) & Importer (`amta/importer.py`):** Exports JSON Schemas (`schemas/*.schema.json`) and provides heuristic migration for legacy Markdown directories.

## Key Technical Decisions

- **Git-native Markdown over external databases:** Storing nodes as plain Markdown with YAML frontmatter keeps project memory reviewable in pull requests without external service dependencies.
- **Deterministic build timestamps:** When `generated_at` is omitted, AMTA derives artifact timestamps from node `updated` dates so `git diff --exit-code` in CI can verify that committed generated artifacts match the source nodes byte-for-byte.
- **Self-dogfooded repository workspace:** The repository includes its own `.amta/` workspace and `schemas/` directory validated on every CI run via `./scripts/ci-check.sh`.

## Verified Evidence and Results

- **Automated Test Suite:** 59 passed `pytest` tests across 9 test modules (`tests/test_builder.py`, `test_cli.py`, `test_config.py`, `test_graph.py`, `test_importer.py`, `test_models.py`, `test_parser.py`, `test_schemas.py`, `test_validator.py`) with **91% line coverage** across `amta/` (804 statements, 76 missed).
- **CI Quality Gate (`.github/workflows/ci.yml`):** Automated GitHub Actions pipeline on Python 3.12 running `ruff check .`, `mypy amta`, `python -m pytest`, `amta validate`, `amta build`, `git diff --check`, and `git diff --exit-code -- .amta/generated schemas`.

## Core commands

```bash
amta init --path .
amta validate
amta build
amta schemas --output schemas
```

## Workspace structure

```text
.amta/
├── config.yml
├── nodes/
├── generated/
│   ├── GRAPH.json
│   ├── MANIFEST.json
│   ├── ROADMAP.md
│   ├── STATE.md
│   └── CHANGELOG.md
└── cache/
```

## Validation

AMTA validates schema correctness, unique node IDs, relation targets, self-references, duplicate edges, graph cycles, configured owners, and orphan nodes.

## Local quality gate

```bash
./scripts/check.sh
```

## Status

Current MVP includes CLI, parser, validator, graph builder, deterministic artifact generation, public JSON Schema export, and a self-dogfooded `.amta/` workspace.

## Limitations

- **Single-workspace local CLI:** Operates on a local directory containing `.amta/`; does not provide a hosted multi-tenant API or remote sync service.
- **Heuristic legacy import:** `amta import-context` uses filename and content heuristics and requires human review before imported nodes are treated as authoritative.
- **Companion template separation:** For the zero-dependency Spanish Markdown starter template (without the Python CLI), see [HiramPeru/Amta](https://github.com/HiramPeru/Amta).

## Operational notes

### Importing existing context

`amta import-context` is a best-effort importer for legacy Markdown context. It infers node types from file names, paths, and content heuristics. Every imported node should be reviewed before it is treated as authoritative project knowledge.

### Generated artifact timestamps

When `generated_at` is not provided explicitly, AMTA derives the artifact timestamp from node `updated` dates to preserve deterministic builds. The derived value is not necessarily the real execution time of the build.

### Development scripts

`scripts/check.sh` is intended to be executed from the root of an initialized AMTA workspace or repository containing `.amta/`.
