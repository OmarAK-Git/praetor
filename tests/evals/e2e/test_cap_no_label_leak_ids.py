from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_no_label_leak_ids_both_arms_pass(tmp_path: Path) -> None:
    rows = {
        row.arm: row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "cap.no_label_leak_ids"
    }
    assert set(rows) == {"old_build", "new_build"}
    for row in rows.values():
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.failure_class == "none"
        assert row.observed["label_leak_found"] is False
        assert "expected_class" not in row.observed["excerpt_blob"]
        assert "EventRecordID=1001" not in row.observed["excerpt_blob"]
        assert "malicious" not in row.observed["alert_identity"]
