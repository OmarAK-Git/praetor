from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import E2E_SCENARIOS_DIR, run_e2e_kernel
from evals.e2e_scenario import load_e2e_scenario
from evals.scorecard import validate_scorecard_row


def test_never_contain_yaml_exists() -> None:
    path = E2E_SCENARIOS_DIR / "gov.never_contain_live_shape.yaml"
    doc = load_e2e_scenario(path)
    assert doc.runner == "e2e_kernel"
    assert doc.theater_detector == "stipulated_capability"


def test_never_contain_both_arms_pass_via_intake(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "gov.never_contain_live_shape"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.failure_class == "none"
        assert row.provider == "fake"
        assert row.observed["final_disposition"] == "escalate"
        assert "never_contain_live_conflict" in row.observed["fault_flags"]
        assert row.observed["directive_emitted"] is False
        assert row.observed["used_process_alert_intake"] is True
