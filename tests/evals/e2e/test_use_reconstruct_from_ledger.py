from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_reconstruct_from_ledger_both_arms(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "use.reconstruct_from_ledger"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.observed["ledger_decision_id_matches"] is True
        assert row.observed["ledger_evidence_bundle_hash_matches"] is True
        assert row.observed["ledger_final_disposition_matches"] is True
