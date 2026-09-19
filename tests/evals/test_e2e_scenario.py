from __future__ import annotations

from pathlib import Path

import pytest
from evals.e2e_scenario import (
    THEATER_DETECTOR_NAMES,
    load_e2e_scenario,
)

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "e2e"
    / "gov.never_contain_live_shape.yaml"
)


def test_loader_reads_required_fields() -> None:
    doc = load_e2e_scenario(FIXTURE)
    assert doc.schema_version == "1"
    assert doc.scenario_id == "gov.never_contain_live_shape"
    assert doc.realm == "governance"
    assert doc.runner == "e2e_kernel"
    assert set(doc.arms) == {"old_build", "new_build"}
    assert doc.arms["old_build"].provider == "fake"
    assert doc.theater_detector == "stipulated_capability"
    assert "final_disposition" in doc.scorecard_pins


def test_filename_stem_must_match_scenario_id(tmp_path: Path) -> None:
    path = tmp_path / "wrong-name.yaml"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="filename stem"):
        load_e2e_scenario(path)


def test_unknown_theater_detector_rejected(tmp_path: Path) -> None:
    text = FIXTURE.read_text(encoding="utf-8").replace(
        "stipulated_capability", "not_a_detector"
    )
    path = tmp_path / "gov.never_contain_live_shape.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="theater_detector"):
        load_e2e_scenario(path)
    assert "label_leak" in THEATER_DETECTOR_NAMES


def test_skip_flag_is_rejected(tmp_path: Path) -> None:
    text = FIXTURE.read_text(encoding="utf-8") + "\nskip: true\n"
    path = tmp_path / "gov.never_contain_live_shape.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected fields"):
        load_e2e_scenario(path)
