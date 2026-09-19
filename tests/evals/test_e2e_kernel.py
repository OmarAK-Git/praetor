from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from evals.e2e_kernel import (
    REQUIRED_E2E_SCENARIO_IDS,
    kernel_exit_code,
    missing_required_scenario_ids,
    run_e2e_kernel,
    scorecards_for_missing_ids,
)
from evals.scorecard import validate_scorecard_row

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_required_ids_are_the_locked_fifteen() -> None:
    assert REQUIRED_E2E_SCENARIO_IDS == frozenset(
        {
            "cap.baseline_bag_path_a",
            "cap.stump_parity_guard",
            "cap.no_label_leak_ids",
            "gov.never_contain_live_shape",
            "gov.feed_unhealthy_blocks_contain",
            "gov.recovery_never_contains",
            "des.envelope_rejects_extra_fields",
            "des.path_b_stays_out_of_src",
            "des.evidence_hash_stable",
            "thr.instruction_in_cmdline",
            "thr.valid_cite_wrong_process",
            "thr.ambiguous_multi_host_target",
            "use.reconstruct_from_ledger",
            "use.progressive_auth_report",
            "use.demo_honesty_gate",
        }
    )


def test_empty_directory_emits_harness_error_rows(tmp_path: Path) -> None:
    empty = tmp_path / "e2e_scenarios"
    empty.mkdir()
    rows = run_e2e_kernel(tmp_root=tmp_path / "db", scenarios_dir=empty)
    missing = missing_required_scenario_ids(set())
    assert missing == REQUIRED_E2E_SCENARIO_IDS
    assert len(rows) == len(REQUIRED_E2E_SCENARIO_IDS)
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "error"
        assert row.failure_class == "harness"
        assert row.arm == "old_build"
    assert kernel_exit_code(rows) == 1


def test_scorecards_for_missing_ids_are_harness_errors() -> None:
    rows = scorecards_for_missing_ids(frozenset({"gov.never_contain_live_shape"}))
    assert rows[0].scenario_id == "gov.never_contain_live_shape"
    assert rows[0].failure_class == "harness"


def test_harness_e2e_flag_exits_zero_after_full_suite() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "evals.harness", "--e2e"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "gov.never_contain_live_shape" in completed.stdout
    assert "cap.no_label_leak_ids" in completed.stdout


def test_full_suite_has_thirty_rows_and_exits_zero(tmp_path: Path) -> None:
    rows = run_e2e_kernel(tmp_root=tmp_path)
    assert len(rows) == 30
    assert {row.scenario_id for row in rows} == REQUIRED_E2E_SCENARIO_IDS
    assert kernel_exit_code(rows) == 0


def test_harness_default_still_runs_outcome_matrix_only() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "evals.harness"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_harness_all_exits_zero_after_full_suite() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "evals.harness", "--all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "gov.never_contain_live_shape" in completed.stdout
    assert "cap.baseline_bag_path_a" in completed.stdout
