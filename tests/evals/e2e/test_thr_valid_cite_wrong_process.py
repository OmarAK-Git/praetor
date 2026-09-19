from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_valid_cite_wrong_process_both_arms(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "thr.valid_cite_wrong_process"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.observed["citations_valid"] is True
        assert row.observed["cite_to_subject"] is False
        assert row.observed["authority_treats_valid_cite_as_right_subject"] is False
        assert row.observed["subject_process_guid"] == (
            "{22222222-2222-2222-2222-222222222222}"
        )
