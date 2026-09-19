from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_progressive_auth_report_both_arms(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "use.progressive_auth_report"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.observed["evaluation_row_present"] is True
        assert row.observed["report_read_only"] is True
        assert row.observed["override_rate_defined"] is True
