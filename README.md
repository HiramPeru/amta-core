# AMTA Core

AMTA Core is a reusable governance engine for Markdown-based project memory.

It turns structured Markdown nodes into validated graph artifacts, generated project views, and JSON schemas for humans, agents, editors, and CI systems.

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
