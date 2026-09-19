from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_feed_unhealthy_blocks_contain_both_arms(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "gov.feed_unhealthy_blocks_contain"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.observed["auto_contain.final_disposition"] == "escalate"
        assert "revocation_feed_unhealthy" in row.observed["auto_contain.fault_flags"]
        assert row.observed["standard_review.final_disposition"] == "standard_review"
        assert row.observed["used_process_alert_intake"] is True
