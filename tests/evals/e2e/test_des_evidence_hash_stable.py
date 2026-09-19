from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_evidence_hash_stable_both_arms(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "des.evidence_hash_stable"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.failure_class == "none"
        assert row.observed["hashes_equal"] is True
        assert row.observed["hash_length"] == 64
