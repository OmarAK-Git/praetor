from __future__ import annotations

from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.real_provider_adversarial import INJECTION_MARKER
from evals.scorecard import validate_scorecard_row


def test_instruction_in_cmdline_survives_excerpt(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "thr.instruction_in_cmdline"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.observed["injection_present_in_excerpts"] is True
        assert row.observed["fake_provider_did_not_obey_injection"] is True
        assert row.observed["live_half"] in {"not_requested", "ran", "error"}
        assert INJECTION_MARKER in row.observed["excerpt_blob"]
