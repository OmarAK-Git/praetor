"""TASK-026 mandatory Phase 2 eval harness tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from evals.harness import (
    SCENARIOS_DIR,
    SCHEMA_PATH,
    format_results,
    list_mandatory_scenarios,
    load_scenario,
    run_all_scenarios,
    run_scenario,
)
from evals.outcome_matrix import (
    ESCALATE_PRODUCING_FAULT_FLAGS,
    OUTCOME_MATRIX_SFE,
    REQUIRED_MATRIX_PAIRS,
    collect_all_scenario_matrix_pairs,
    scenario_asserts_ticket_stamp_failed,
)

from praetor.metrics.events import OutcomeMatrixFaultFlag

REPO_ROOT = Path(__file__).resolve().parents[2]


def _all_scenario_ids() -> list[str]:
    return [scenario.scenario_id for scenario in list_mandatory_scenarios()]


def test_mandatory_scenario_files_present() -> None:
    paths = sorted(SCENARIOS_DIR.glob("*.yaml"))
    assert len(paths) >= 24
    for path in paths:
        scenario = load_scenario(path)
        assert scenario.scenario_id == path.stem


def test_scenarios_validate_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["title"] == "PraetorEvalScenario"
    for scenario in list_mandatory_scenarios():
        assert scenario.schema_version == "1"


@pytest.mark.parametrize("scenario_id", _all_scenario_ids())
def test_each_scenario_loads(scenario_id: str) -> None:
    scenario = load_scenario(SCENARIOS_DIR / f"{scenario_id}.yaml")
    assert scenario.scenario_id == scenario_id
    assert scenario.runner
    assert scenario.expectations


def test_scenario_fault_flags_are_canonical_enum_values() -> None:
    for scenario in list_mandatory_scenarios():
        expectations = scenario.expectations
        if scenario.runner == "revocation_feed_degraded_mode":
            blocks = [
                expectations.get("auto_contain"),
                expectations.get("standard_review"),
            ]
            flags: list[str] = []
            for block in blocks:
                if isinstance(block, dict):
                    flags.extend(block.get("fault_flags", []))
        else:
            flags = list(expectations.get("fault_flags", []))
        for flag in flags:
            OutcomeMatrixFaultFlag(flag)


def test_scenario_sfe_polarity_matches_canonical_map() -> None:
    for scenario in list_mandatory_scenarios():
        expectations = scenario.expectations
        blocks: list[tuple[str, dict[str, object]]] = []
        if scenario.runner == "revocation_feed_degraded_mode":
            for key in ("auto_contain", "standard_review"):
                block = expectations.get(key)
                if isinstance(block, dict):
                    blocks.append((key, block))
        else:
            blocks.append(("", dict(expectations)))

        for label, block in blocks:
            flags = block.get("fault_flags", [])
            if not flags:
                continue
            prefix = (
                f"{scenario.scenario_id}/{label}: "
                if label
                else f"{scenario.scenario_id}: "
            )
            assert "system_fault_escalation" in block, (
                f"{prefix}fault_flags present but system_fault_escalation missing"
            )
            actual_sfe = bool(block["system_fault_escalation"])
            for flag in flags:
                canonical = OUTCOME_MATRIX_SFE[OutcomeMatrixFaultFlag(flag)]
                assert actual_sfe == canonical, (
                    f"{prefix}{flag!r} expected SFE {canonical}, "
                    f"scenario has {actual_sfe}"
                )


def test_outcome_matrix_completeness_guard() -> None:
    scenarios = list_mandatory_scenarios()
    covered = collect_all_scenario_matrix_pairs(scenarios)
    missing = REQUIRED_MATRIX_PAIRS - covered
    assert missing == set(), (
        "Outcome Matrix escalate rows missing scenario coverage: "
        + ", ".join(f"{flag}(SFE={sfe})" for flag, sfe in sorted(missing))
    )
    assert covered >= REQUIRED_MATRIX_PAIRS
    assert len(covered) == len(ESCALATE_PRODUCING_FAULT_FLAGS)


def test_ticket_stamp_failed_scenario_present() -> None:
    scenarios = list_mandatory_scenarios()
    assert any(
        scenario_asserts_ticket_stamp_failed(scenario.expectations)
        for scenario in scenarios
    )


def test_harness_all_scenarios_pass(tmp_path: Path) -> None:
    results = run_all_scenarios(tmp_root=tmp_path)
    assert len(results) == len(list_mandatory_scenarios())
    failures = [result for result in results if not result.passed]
    assert failures == [], format_results(failures)


def test_harness_main_exits_zero_on_success() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "evals.harness"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_harness_reports_scenario_failure(tmp_path: Path) -> None:
    from evals.harness import ScenarioDocument

    scenario = load_scenario(SCENARIOS_DIR / "benign_admin_activity.yaml")
    assert run_scenario(scenario, db_path=tmp_path / "ok.db").passed

    broken = ScenarioDocument(
        schema_version=scenario.schema_version,
        scenario_id=scenario.scenario_id,
        description=scenario.description,
        runner=scenario.runner,
        setup=scenario.setup,
        expectations={
            **dict(scenario.expectations),
            "final_disposition": "escalate",
            "fault_flags": ["correlation_failure"],
            "system_fault_escalation": True,
        },
        source_path=scenario.source_path,
    )
    result = run_scenario(broken, db_path=tmp_path / "broken.db")
    assert not result.passed
    assert result.errors
