from __future__ import annotations

from pathlib import Path

import pytest
from evals.theater import TheaterContext, run_theater_detector


def _ctx(**overrides: object) -> TheaterContext:
    payload: dict[str, object] = {
        "scenario_id": "cap.no_label_leak_ids",
        "realm": "capability",
        "arm": "old_build",
        "alert_identity": "cap.no_label_leak_ids",
        "excerpt_blob": "process_name=cmd.exe command_line=whoami",
        "scorecard_status": "pass",
        "scorecard_is_quality_pass": False,
        "src_root": Path("src/praetor"),
        "copy_roots": (),
        "cite_to_subject_primary_earned": False,
    }
    payload.update(overrides)
    return TheaterContext(**payload)  # type: ignore[arg-type]


def test_unknown_detector_raises() -> None:
    with pytest.raises(KeyError, match="unknown theater"):
        run_theater_detector("not_a_detector", _ctx())


def test_label_leak_trips_on_expected_class_in_excerpt() -> None:
    finding = run_theater_detector(
        "label_leak",
        _ctx(excerpt_blob="expected_class=malicious seed EventRecordID=1001"),
    )
    assert finding.tripped is True
    assert finding.detector == "label_leak"


def test_stipulated_capability_trips_on_quality_pass() -> None:
    finding = run_theater_detector(
        "stipulated_capability",
        _ctx(
            scenario_id="cap.baseline_bag_path_a",
            realm="capability",
            scorecard_is_quality_pass=True,
        ),
    )
    assert finding.tripped is True


def test_unearned_demo_claim_trips_when_primary_unearned(tmp_path: Path) -> None:
    copy = tmp_path / "README.md"
    copy.write_text("Praetor judgment works and is production-ready.\n", encoding="utf-8")
    finding = run_theater_detector(
        "unearned_demo_claim",
        _ctx(copy_roots=(tmp_path,), cite_to_subject_primary_earned=False),
    )
    assert finding.tripped is True


def test_path_b_in_src_trips_on_flatten_import(tmp_path: Path) -> None:
    pkg = tmp_path / "praetor"
    pkg.mkdir()
    (pkg / "smuggle.py").write_text(
        "from evals.capability.flatten import flatten_event\n",
        encoding="utf-8",
    )
    finding = run_theater_detector("path_b_in_src", _ctx(src_root=tmp_path))
    assert finding.tripped is True


def test_gate_scored_as_judgment_trips_on_quality_from_policy_gate() -> None:
    finding = run_theater_detector(
        "gate_scored_as_judgment",
        _ctx(
            scenario_id="cap.baseline_bag_path_a",
            scorecard_is_quality_pass=True,
            excerpt_blob="scored_layer=policy_gate",
        ),
    )
    assert finding.tripped is True
