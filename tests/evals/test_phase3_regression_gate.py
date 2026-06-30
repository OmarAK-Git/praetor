"""TASK-031: Phase 3 regression gate tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml
from evals.correlation_gate import (
    REPO_ROOT,
    load_correlation_expected,
    run_correlation_gate,
)
from evals.run_phase3_gate import (
    INCIDENT_HOST_ID,
    NOISE_HOST_ID,
    REQUIRED_EXPECTED_PATH,
    REQUIRED_EXPECTED_SCENARIO_ID,
    check_account_containment_prerequisite,
    check_identity_compliance_evidence,
    check_noisy_correlation_accuracy,
    check_phase2_safety_on_noisy_bundle,
    check_required_expected_file,
    correlate_bundle_from_expected,
    run_phase3_gate,
)

from praetor.evidence.provenance import meets_account_corroboration


def test_required_expected_file_present() -> None:
    result = check_required_expected_file()
    assert result.passed is True
    assert REQUIRED_EXPECTED_PATH.is_file()


def test_gate_fails_when_expected_file_absent(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    result = check_required_expected_file(expected_path=missing)
    assert result.passed is False
    assert any("missing human-authored expected output" in error for error in result.errors)


def test_noisy_correlation_expected_yaml_has_binding_bounds() -> None:
    scenario = load_correlation_expected(REQUIRED_EXPECTED_PATH)
    expectations = scenario.expectations
    excluded = expectations.get("excluded_record_ids", [])
    assert "9999" in excluded
    assert "1004" in excluded
    assert expectations.get("max_noise_overcollection") == 1
    assert expectations.get("max_collected_facts") == 4


def test_noisy_correlation_gate_passes_on_healthy_tree() -> None:
    gate = run_correlation_gate(REQUIRED_EXPECTED_PATH, repo_root=REPO_ROOT)
    assert gate.scenario_id == REQUIRED_EXPECTED_SCENARIO_ID
    assert gate.passed is True, gate.errors
    assert set(gate.collected_record_ids) == {"1001", "1002", "1003", "2001"}
    assert set(gate.collected_noise_record_ids) == {"1003"}
    assert gate.noise_overcollection == 1


def test_window_excludes_out_of_window_record_9999() -> None:
    gate = run_correlation_gate(REQUIRED_EXPECTED_PATH, repo_root=REPO_ROOT)
    assert gate.passed is True, gate.errors
    assert "9999" not in gate.collected_record_ids


def test_noisy_correlation_accuracy_check_passes() -> None:
    result = check_noisy_correlation_accuracy()
    assert result.passed is True, result.errors


def test_noisy_correlation_gate_fails_on_zero_noise_threshold(tmp_path: Path) -> None:
    scenario = load_correlation_expected(REQUIRED_EXPECTED_PATH)
    scenario.raw["expectations"]["max_noise_overcollection"] = 0
    tampered = tmp_path / "zero_noise.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any("noise overcollection" in error for error in result.errors)
    assert any("1003" in error for error in result.errors)


def test_correlator_should_drop_cross_host_in_window_noise() -> None:
    gate = run_correlation_gate(REQUIRED_EXPECTED_PATH, repo_root=REPO_ROOT)
    assert "1004" not in gate.collected_record_ids


def test_noisy_bundle_consumes_task28_correlation_output() -> None:
    bundle = correlate_bundle_from_expected(REQUIRED_EXPECTED_PATH, repo_root=REPO_ROOT)
    assert bundle.facts
    assert all(fact.raw_source for fact in bundle.facts)
    assert meets_account_corroboration(bundle.facts) is True


def test_phase2_safety_on_noisy_correlated_bundle() -> None:
    result = check_phase2_safety_on_noisy_bundle()
    assert result.passed is True, result.errors


def test_phase2_safety_targets_incident_host_not_noise_host() -> None:
    result = check_phase2_safety_on_noisy_bundle()
    assert result.passed is True, result.errors
    bundle = correlate_bundle_from_expected(REQUIRED_EXPECTED_PATH, repo_root=REPO_ROOT)
    host_ids = {
        fact.normalized_fields.get("host_id")
        for fact in bundle.facts
        if fact.normalized_fields.get("host_id")
    }
    assert INCIDENT_HOST_ID in host_ids
    assert NOISE_HOST_ID not in host_ids


def test_account_containment_requires_identity_compliance() -> None:
    preflight = check_account_containment_prerequisite()
    assert preflight.passed is True, preflight.errors

    identity = check_identity_compliance_evidence(repo_root=REPO_ROOT)
    assert identity.passed is True, identity.errors


def test_phase3_gate_stops_when_expected_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    results = run_phase3_gate(
        expected_path=missing,
        include_harness=False,
        include_identity_subprocess=False,
    )
    assert len(results) == 1
    assert results[0].name == "required_expected_file"
    assert results[0].passed is False


def test_run_phase3_gate_core_checks_pass(tmp_path: Path) -> None:
    results = run_phase3_gate(
        include_harness=False,
        include_identity_subprocess=False,
        tmp_root=tmp_path,
    )
    names = [result.name for result in results]
    assert names == [
        "required_expected_file",
        "noisy_correlation_accuracy",
        "account_containment_prerequisite",
        "phase2_safety_on_noisy_bundle",
    ]
    failures = [result for result in results if not result.passed]
    assert failures == [], [
        f"{failure.name}: {failure.errors}" for failure in failures
    ]


def test_phase3_gate_cli_exits_zero_on_success() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "evals.run_phase3_gate",
            "--skip-harness",
            "--skip-identity-subprocess",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "PASS required_expected_file" in completed.stdout
    assert "PASS noisy_correlation_accuracy" in completed.stdout
    assert "PASS phase2_safety_on_noisy_bundle" in completed.stdout
