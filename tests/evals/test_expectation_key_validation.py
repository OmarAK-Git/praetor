"""V2-036: CI guard for stale and unknown harness expectation keys."""

from __future__ import annotations

import pytest
from evals.harness import (
    ALL_EXPECTATION_KEYS,
    RUNNER_EXPECTATION_KEYS,
    _validate_expectations,
    list_mandatory_scenarios,
)


def test_expectation_key_registry_is_complete() -> None:
    covered = frozenset().union(*RUNNER_EXPECTATION_KEYS.values())
    assert covered == ALL_EXPECTATION_KEYS


@pytest.mark.parametrize(
    "scenario_id",
    [scenario.scenario_id for scenario in list_mandatory_scenarios()],
)
def test_mandatory_scenario_expectation_keys_are_valid(scenario_id: str) -> None:
    scenario = next(
        item for item in list_mandatory_scenarios() if item.scenario_id == scenario_id
    )
    errors = _validate_expectations(
        runner=scenario.runner,
        expectations=scenario.expectations,
    )
    assert errors == [], f"{scenario_id}: {errors}"


def test_unknown_expectation_key_rejected() -> None:
    errors = _validate_expectations(
        runner="engine_intake",
        expectations={
            "final_disposition": "escalate",
            "fault_flags": [],
            "system_fault_escalation": False,
            "stale_typo_key": True,
        },
    )
    assert any("unknown expectation key" in error for error in errors)


def test_stale_expectation_key_wrong_runner_rejected() -> None:
    errors = _validate_expectations(
        runner="prompt_isolation",
        expectations={
            "raw_source_excluded": True,
            "excerpt_max_chars": 200,
            "final_disposition": "escalate",
        },
    )
    assert any("not consumed by runner" in error for error in errors)


def test_revocation_nested_unknown_expectation_key_rejected() -> None:
    errors = _validate_expectations(
        runner="revocation_feed_degraded_mode",
        expectations={
            "auto_contain": {
                "final_disposition": "escalate",
                "fault_flags": ["revocation_feed_unhealthy"],
                "system_fault_escalation": True,
                "stale_nested_key": True,
            },
            "standard_review": {
                "final_disposition": "standard_review",
                "fault_flags": [],
                "system_fault_escalation": False,
            },
        },
    )
    assert any("unknown nested expectation key" in error for error in errors)
