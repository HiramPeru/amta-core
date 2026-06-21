"""Import legacy project context into AMTA nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from amta.config import WORKSPACE_DIRNAME
from amta.models import NODE_ID_PATTERN, TYPE_PREFIXES, NodeModel, NodeStatus, NodeType

IMPORT_SOURCE_DIRS = (
    Path("context"),
    Path("Data") / "Docs",
)

IMPORTED_FROM_PATTERN = re.compile(r"Imported from:\s*`([^`]+)`")


class AmtaImportError(Exception):
    """Raised when AMTA context import cannot proceed."""


@dataclass(frozen=True)
class ImportWarning:
    """Non-fatal import warning."""

    code: str
    message: str
    source_path: Path | None = None


@dataclass(frozen=True)
class ImportedNode:
    """Imported node record."""

    source_path: Path
    node_path: Path
    node_id: str


@dataclass
class ImportContextResult:
    """Import result."""

    imported_nodes: list[ImportedNode] = field(default_factory=list)
    warnings: list[ImportWarning] = field(default_factory=list)


def import_context(
    root_path: str | Path,
    *,
    overwrite: bool = False,
    import_date: date | None = None,
) -> ImportContextResult:
    """Import legacy context markdown files into .amta/nodes."""
    root = Path(root_path).resolve()

    if not root.exists():
        raise AmtaImportError(f"Repository path does not exist: {root}")

    if not root.is_dir():
        raise AmtaImportError(f"Repository path is not a directory: {root}")

    workspace_dir = root / WORKSPACE_DIRNAME
    nodes_dir = workspace_dir / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)

    result = ImportContextResult()
    source_files = _discover_source_files(root)

    if not source_files:
        result.warnings.append(
            ImportWarning(
                code="IMP-W001",
                message="No importable markdown files found under context/ or Data/Docs.",
            )
        )
        return result

    existing_sources = _read_existing_imported_sources(nodes_dir)
    used_ids = _read_existing_node_ids(nodes_dir)
    counters = _initial_counters(used_ids)
    effective_date = import_date or date.today()

    for source_file in source_files:
        source_rel = _relative_posix(root, source_file)
        existing_node_path = existing_sources.get(source_rel)

        if existing_node_path and not overwrite:
            result.warnings.append(
                ImportWarning(
                    code="IMP-W002",
                    message=f"Source already imported as {existing_node_path.name}; skipping.",
                    source_path=source_file,
                )
            )
            continue

        content = source_file.read_text(encoding="utf-8")
        title = _infer_title(source_file, content)
        if title == source_file.stem.replace("-", " ").replace("_", " ").title():
            result.warnings.append(
                ImportWarning(
                    code="IMP-W003",
                    message="No markdown H1 found; inferred title from filename.",
                    source_path=source_file,
                )
            )

        if existing_node_path and overwrite:
            node_id = existing_node_path.stem
            node_type = _node_type_from_id(node_id)
            node_path = existing_node_path
        else:
            node_type = _infer_node_type(source_file, content)
            node_id = _allocate_node_id(node_type, used_ids, counters)
            node_path = nodes_dir / f"{node_id}.md"

        body = _build_imported_body(source_rel, content)
        metadata = {
            "id": node_id,
            "type": node_type.value,
            "status": NodeStatus.ACTIVE.value,
            "title": title,
            "summary": _infer_summary(title, content),
            "owner": "architecture",
            "revision": 1,
            "created": effective_date.isoformat(),
            "updated": effective_date.isoformat(),
            "tags": _infer_tags(source_file, node_type),
            "relations": [],
            "body": body,
        }

        node = NodeModel.model_validate(metadata)
        _write_node(node_path, node)

        result.imported_nodes.append(
            ImportedNode(
                source_path=source_file,
                node_path=node_path,
                node_id=node_id,
            )
        )

    return result


def _discover_source_files(root: Path) -> list[Path]:
    files: list[Path] = []

    for source_dir in IMPORT_SOURCE_DIRS:
        candidate_dir = root / source_dir
        if not candidate_dir.is_dir():
            continue

        files.extend(
            path
            for path in sorted(candidate_dir.rglob("*.md"))
            if path.is_file() and WORKSPACE_DIRNAME not in path.parts
        )

    return sorted(files, key=lambda path: _relative_posix(root, path))


def _read_existing_imported_sources(nodes_dir: Path) -> dict[str, Path]:
    imported_sources: dict[str, Path] = {}

    if not nodes_dir.is_dir():
        return imported_sources

    for node_file in sorted(nodes_dir.glob("*.md")):
        content = node_file.read_text(encoding="utf-8")
        match = IMPORTED_FROM_PATTERN.search(content)
        if match:
            imported_sources[match.group(1)] = node_file

    return imported_sources


def _read_existing_node_ids(nodes_dir: Path) -> set[str]:
    if not nodes_dir.is_dir():
        return set()

    return {
        node_file.stem
        for node_file in nodes_dir.glob("*.md")
        if NODE_ID_PATTERN.fullmatch(node_file.stem)
    }


def _initial_counters(used_ids: set[str]) -> dict[NodeType, int]:
    counters = {node_type: 0 for node_type in NodeType}

    for node_id in used_ids:
        prefix, number_text = node_id.split("-", 1)
        for node_type, expected_prefix in TYPE_PREFIXES.items():
            if prefix == expected_prefix:
                counters[node_type] = max(counters[node_type], int(number_text))

    return counters


def _allocate_node_id(
    node_type: NodeType,
    used_ids: set[str],
    counters: dict[NodeType, int],
) -> str:
    prefix = TYPE_PREFIXES[node_type]

    while True:
        counters[node_type] += 1
        candidate = f"{prefix}-{counters[node_type]:03d}"
        if candidate not in used_ids:
            used_ids.add(candidate)
            return candidate


def _node_type_from_id(node_id: str) -> NodeType:
    prefix = node_id.split("-", 1)[0]
    for node_type, expected_prefix in TYPE_PREFIXES.items():
        if prefix == expected_prefix:
            return node_type

    raise AmtaImportError(f"Cannot infer node type from existing id: {node_id}")


def _infer_node_type(source_file: Path, content: str) -> NodeType:
    haystack = f"{source_file.as_posix()} {content[:1000]}".lower()

    if any(token in haystack for token in ("adr", "decision", "decisión", "decision-log")):
        return NodeType.DECISION

    if any(token in haystack for token in ("roadmap", "task", "todo", "pending", "pendiente")):
        return NodeType.TASK

    if any(
        token in haystack
        for token in ("constraint", "security", "seguridad", "rls", "auth", "policy")
    ):
        return NodeType.CONSTRAINT

    if any(
        token in haystack
        for token in ("incident", "incidente", "bug", "error", "failure", "fallo")
    ):
        return NodeType.INCIDENT

    if any(token in haystack for token in ("module", "módulo", "architecture", "arquitectura")):
        return NodeType.MODULE

    return NodeType.EVENT


def _infer_title(source_file: Path, content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return _clamp_text(stripped[2:].strip(), max_length=200)

    fallback = source_file.stem.replace("-", " ").replace("_", " ").title()
    return _clamp_text(fallback, max_length=200)


def _infer_summary(title: str, content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        return _clamp_text(stripped, max_length=500)

    return _clamp_text(f"Imported legacy context document: {title}.", max_length=500)


def _infer_tags(source_file: Path, node_type: NodeType) -> list[str]:
    tags = ["imported", node_type.value]

    parts = [part.lower() for part in source_file.parts]
    if "context" in parts:
        tags.append("context")
    if "data" in parts or "docs" in parts:
        tags.append("data-docs")

    for candidate in ("security", "finance", "crm", "whatsapp", "performance", "architecture"):
        if candidate in source_file.as_posix().lower():
            tags.append(candidate)

    deduped: list[str] = []
    for tag in tags:
        normalized = _normalize_tag(tag)
        if normalized not in deduped:
            deduped.append(normalized)

    return deduped


def _normalize_tag(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9_-]+", "-", value.lower()).strip("-")
    if not normalized or not re.fullmatch(r"^[a-z][a-z0-9_-]*$", normalized):
        return "imported"
    return normalized


def _build_imported_body(source_rel: str, content: str) -> str:
    return (
        "# Imported Context\n\n"
        f"Imported from: `{source_rel}`\n\n"
        "## Original Content\n\n"
        f"{content.strip()}\n"
    )


def _write_node(node_path: Path, node: NodeModel) -> None:
    frontmatter_data = node.model_dump(mode="json", exclude={"body"})
    frontmatter_text = yaml.safe_dump(
        frontmatter_data,
        sort_keys=False,
        allow_unicode=True,
    )

    node_path.write_text(
        f"---\n{frontmatter_text}---\n\n{node.body.rstrip()}\n",
        encoding="utf-8",
    )


def _clamp_text(value: str, *, max_length: int) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 1].rstrip() + "…"


def _relative_posix(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()
