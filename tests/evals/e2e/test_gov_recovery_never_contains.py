from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_recovery_never_contains_both_arms(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "gov.recovery_never_contains"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.observed["recovered_final_disposition"] == "escalate"
        assert row.observed["recovered_proposed_disposition"] == "auto_contain"
        assert row.observed["containment_directive_emitted"] is False
        assert row.observed["used_run_engine_startup_recovery"] is True
