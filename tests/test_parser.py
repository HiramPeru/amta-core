from pathlib import Path

import pytest

from amta.errors import AmtaParseError
from amta.parser import parse_node_file, parse_nodes_dir, parse_workspace_nodes


def write_node(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parse_node_file_valid() -> None:
    path = Path("tests/.tmp_DEC_001.md")
    try:
        write_node(
            path,
            """
---
id: DEC-001
type: decision
status: active
title: Graph as Source of Truth
summary: Graph becomes the canonical operational representation.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags:
  - architecture
relations:
  - type: impacts
    target: MOD-001
---

# Context

Body.
""".lstrip(),
        )

        node = parse_node_file(path)

        assert node.id == "DEC-001"
        assert node.relations[0].type == "impacts"
        assert node.relations[0].target == "MOD-001"
        assert node.body == "# Context\n\nBody."
    finally:
        path.unlink(missing_ok=True)


def test_parse_node_file_supports_yaml_multiline(tmp_path: Path) -> None:
    node_path = tmp_path / "DEC-001.md"
    write_node(
        node_path,
        """
---
id: DEC-001
type: decision
status: active
title: Multiline Summary
summary: >
  This is a multiline summary
  that YAML should fold correctly.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations: []
---

# Body

Markdown can contain --- safely after frontmatter.
""".lstrip(),
    )

    node = parse_node_file(node_path)

    assert "This is a multiline summary" in node.summary
    assert "that YAML should fold correctly." in node.summary
    assert "--- safely" in node.body


def test_parse_node_file_rejects_missing_frontmatter(tmp_path: Path) -> None:
    node_path = tmp_path / "DEC-001.md"
    write_node(node_path, "# No frontmatter\n")

    with pytest.raises(AmtaParseError, match="Missing frontmatter"):
        parse_node_file(node_path)


def test_parse_node_file_rejects_invalid_metadata(tmp_path: Path) -> None:
    node_path = tmp_path / "DEC-001.md"
    write_node(
        node_path,
        """
---
id: DEC-001
type: task
status: active
title: Wrong Prefix
summary: This should fail because DEC is not task.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations: []
---

Body.
""".lstrip(),
    )

    with pytest.raises(AmtaParseError, match="Invalid node metadata"):
        parse_node_file(node_path)


def test_parse_nodes_dir_is_deterministic(tmp_path: Path) -> None:
    nodes_dir = tmp_path / "nodes"
    write_node(
        nodes_dir / "TSK-002.md",
        """
---
id: TSK-002
type: task
status: active
title: Second
summary: Second task.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations: []
---

Second.
""".lstrip(),
    )
    write_node(
        nodes_dir / "DEC-001.md",
        """
---
id: DEC-001
type: decision
status: active
title: First
summary: First decision.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations: []
---

First.
""".lstrip(),
    )

    nodes = parse_nodes_dir(nodes_dir)

    assert [node.id for node in nodes] == ["DEC-001", "TSK-002"]


def test_parse_workspace_nodes(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".amta"
    nodes_dir = workspace_dir / "nodes"
    write_node(
        nodes_dir / "EVT-001.md",
        """
---
id: EVT-001
type: event
status: completed
title: Bootstrap
summary: AMTA workspace bootstrap event.
owner: architecture
revision: 1
created: 2026-06-21
updated: 2026-06-21
tags: []
relations: []
---

Bootstrap.
""".lstrip(),
    )

    nodes = parse_workspace_nodes(workspace_dir)

    assert len(nodes) == 1
    assert nodes[0].id == "EVT-001"
