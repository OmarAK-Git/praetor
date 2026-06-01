from pathlib import Path

import yaml

import praetor

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFEST_PATH = FIXTURES_DIR / "fixture_manifest.yaml"


def test_import_praetor() -> None:
    assert praetor.__version__


def test_fixture_manifest_loads() -> None:
    assert MANIFEST_PATH.is_file()
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["version"] == "1"
    assert data["fixtures"] == []
