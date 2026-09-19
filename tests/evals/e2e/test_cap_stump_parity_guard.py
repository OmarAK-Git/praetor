from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_stump_parity_guard_does_not_claim_quality_win(tmp_path: Path) -> None:
    rows = {
        row.arm: row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "cap.stump_parity_guard"
    }
    assert set(rows) == {"old_build", "new_build"}
    for row in rows.values():
        validate_scorecard_row(row)
        assert row.observed["quality_win_claimed"] is False
        assert "stump_correct" in row.observed
        assert "model_correct" in row.observed
        assert row.observed["path_a_fact_count"] >= 1
    assert rows["old_build"].status == "pass"
    assert rows["new_build"].status == "pending"
