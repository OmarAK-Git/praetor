"""V2-024 harness scenario for enabled account auto_contain."""

from __future__ import annotations

from pathlib import Path

from evals.harness import SCENARIOS_DIR, load_scenario, run_scenario


def test_account_containment_enabled_harness_scenario(tmp_path: Path) -> None:
    scenario = load_scenario(
        SCENARIOS_DIR / "account_containment_enabled.yaml",
    )
    result = run_scenario(scenario, db_path=tmp_path / "state.db")
    assert result.passed is True, result.errors
