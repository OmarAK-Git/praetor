"""V2-020 eval harness metrics expectation tests."""

from __future__ import annotations

from pathlib import Path

from evals.harness import SCENARIOS_DIR, load_scenario, run_scenario


def test_provider_unavailable_scenario_asserts_llm_failure_metrics(
    tmp_path: Path,
) -> None:
    scenario = load_scenario(SCENARIOS_DIR / "provider_unavailable.yaml")
    result = run_scenario(scenario, db_path=tmp_path / "state.db")
    assert result.passed, result.errors


def test_correlation_failure_scenario_asserts_no_llm_failure_metrics(
    tmp_path: Path,
) -> None:
    scenario = load_scenario(SCENARIOS_DIR / "correlation_failure.yaml")
    metrics = scenario.expectations.get("metrics")
    assert isinstance(metrics, dict)
    assert metrics.get("llm_failure_by_fault_flag") == {}
    result = run_scenario(scenario, db_path=tmp_path / "state.db")
    assert result.passed, result.errors
