# Changelog

## 0.2.2-dev

- Add coverage for `amta query --direction both`.
- Update project changelog through `v0.2.1-dev`.

## 0.2.1-dev

- Document query traversal implementation tradeoff.
- Record manual adjacency indexing as an intentional MVP implementation with future NetworkX traversal consideration.

## 0.2.0-dev

- Add experimental `amta query` command.
- Support `--direction upstream`, `--direction downstream`, and `--direction both`.
- Support bounded traversal with `--depth`.
- Add CLI tests for downstream, upstream, and missing-node query behavior.

## 0.1.2-dev

- Fix generated `STATE.md` so graph health reflects the real `ValidationStatus`.
- Pass validation status from the CLI build command into artifact generation.
- Add tests for `PASS`, `WARN`, and `FAIL` state rendering.
- Clean Python cache hygiene and update `.gitignore`.
- Document importer best-effort behavior, deterministic generated timestamps, and development script assumptions.

## 0.1.1-dev

- Add legacy context importer.
- Support importing existing Markdown context into AMTA nodes.
- Document imported nodes as review-required best-effort output.

## 0.1.0-dev

- Initial AMTA Core MVP.
- Add CLI, parser, validator, graph builder, deterministic artifact generation, JSON schema export, tests, CI, and self-dogfooded `.amta/` workspace.
