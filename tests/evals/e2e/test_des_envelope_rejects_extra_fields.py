from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row


def test_envelope_rejects_extra_fields_both_arms(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "des.envelope_rejects_extra_fields"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.observed["raises_validation_error"] is True
        assert row.observed["accepted_legal_envelope"] is True
        assert row.observed["rejected_cbc_field"] == "cbc_edr_alert"
