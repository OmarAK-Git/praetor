from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_ambiguous_multi_host_both_arms(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "thr.ambiguous_multi_host_target"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.observed["final_disposition"] == "escalate"
        assert row.observed["fault_flags"] == ["ambiguous_containment_target"]
        assert row.observed["used_process_alert_intake"] is True
