from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_baseline_bag_path_a_old_pass_new_pending(tmp_path: Path) -> None:
    rows = {
        row.arm: row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "cap.baseline_bag_path_a"
    }
    assert set(rows) == {"old_build", "new_build"}
    for row in rows.values():
        validate_scorecard_row(row)
        assert row.observed["path_a_event_ids"] == [1, 4624]
        assert row.observed["used_correlate_telemetry"] is True
        assert row.observed["used_process_alert_intake"] is True
        assert row.observed["used_path_b"] is False
        assert "malicious" not in str(row.observed.get("alert_identity", ""))
    assert rows["old_build"].status == "pass"
    assert rows["new_build"].status == "pending"
    assert rows["new_build"].failure_class == "none"
