import json
from pathlib import Path

from amta.schemas import SCHEMA_FILENAMES, get_schemas, write_schemas


def test_get_schemas_contains_public_model_schemas() -> None:
    schemas = get_schemas()

    assert set(schemas) == {"node", "config", "graph"}
    assert schemas["node"]["title"] == "NodeModel"
    assert schemas["config"]["title"] == "ConfigModel"
    assert schemas["graph"]["title"] == "GraphModel"


def test_write_schemas_writes_json_files(tmp_path: Path) -> None:
    written = write_schemas(tmp_path)

    assert set(written) == set(SCHEMA_FILENAMES)
    for filename in SCHEMA_FILENAMES.values():
        path = tmp_path / filename
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "properties" in payload
