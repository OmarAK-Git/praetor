"""Deterministic JSON Schema artifact export (B-004)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from praetor.contracts.schema_export import (
    SCHEMA_EXPORTS,
    canonical_schema_bytes,
    export_schemas,
)

EXPECTED_SCHEMA_FILES = {filename for _, filename in SCHEMA_EXPORTS}


@pytest.fixture
def schemas_dir(tmp_path: Path) -> Path:
    return tmp_path / "schemas"


def test_schema_export_inventory(schemas_dir: Path) -> None:
    written = export_schemas(schemas_dir)
    names = {path.name for path in written}
    assert names == EXPECTED_SCHEMA_FILES


def test_schema_export_includes_schema_version(schemas_dir: Path) -> None:
    export_schemas(schemas_dir)
    for _, filename in SCHEMA_EXPORTS:
        schema = json.loads((schemas_dir / filename).read_text(encoding="utf-8"))
        props = schema.get("properties", {})
        assert "schema_version" in props, filename


def test_schema_export_is_byte_stable(schemas_dir: Path) -> None:
    export_schemas(schemas_dir)
    first = {p.name: p.read_bytes() for p in schemas_dir.glob("*.json")}
    export_schemas(schemas_dir)
    second = {p.name: p.read_bytes() for p in schemas_dir.glob("*.json")}
    assert first == second


def test_canonical_schema_bytes_sorted() -> None:
    b = canonical_schema_bytes({"z": 1, "a": 2})
    assert b.index(b'"a"') < b.index(b'"z"')
