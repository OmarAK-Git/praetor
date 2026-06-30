"""TASK-030: correlation accuracy gate tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from evals.correlation_gate import (
    EXPECTED_DIR,
    REPO_ROOT,
    load_correlation_expected,
    run_correlation_gate,
    verify_fixture_manifest_checksums,
)

PASS_SCENARIO = EXPECTED_DIR / "otrf_process_chain_corroborated_logon.yaml"
NOISY_SCENARIO = EXPECTED_DIR / "otrf_noisy_in_window_bounded.yaml"
UNRELATED_NOISE_SCENARIO = EXPECTED_DIR / "otrf_unrelated_in_window_noise.yaml"
WINDOW_SCENARIO = EXPECTED_DIR / "otrf_window_boundary.yaml"
MANIFEST_PATH = REPO_ROOT / "tests" / "fixtures" / "fixture_manifest.yaml"


def test_manifest_checksum_verified_before_gate() -> None:
    result = verify_fixture_manifest_checksums(MANIFEST_PATH, repo_root=REPO_ROOT)
    assert result.passed is True
    assert not result.errors


def test_gate_passes_known_otrf_scenario() -> None:
    result = run_correlation_gate(PASS_SCENARIO, repo_root=REPO_ROOT)
    assert result.passed is True, result.errors
    assert result.scenario_id == "otrf_process_chain_corroborated_logon"
    assert set(result.collected_record_ids) == {"1001", "1002", "2001"}
    assert result.noise_overcollection == 0
    assert result.collected_noise_record_ids == ()


def test_gate_passes_noise_below_threshold() -> None:
    result = run_correlation_gate(NOISY_SCENARIO, repo_root=REPO_ROOT)
    assert result.passed is True, result.errors
    assert result.scenario_id == "otrf_noisy_in_window_bounded"
    assert set(result.collected_record_ids) == {"1001", "1002", "1003", "2001"}
    assert result.collected_noise_record_ids == ("1003",)
    assert result.noise_overcollection == 1


def test_gate_passes_unrelated_in_window_noise_below_threshold() -> None:
    result = run_correlation_gate(UNRELATED_NOISE_SCENARIO, repo_root=REPO_ROOT)
    assert result.passed is True, result.errors
    assert set(result.collected_record_ids) == {"1001", "1002", "2001"}
    assert result.collected_noise_record_ids == ()
    assert result.noise_overcollection == 0


def test_gate_fails_when_cross_host_record_required(tmp_path: Path) -> None:
    scenario = load_correlation_expected(UNRELATED_NOISE_SCENARIO)
    scenario.raw["expectations"]["required_record_ids"].append("1004")
    scenario.raw["expectations"]["excluded_record_ids"] = []
    tampered = tmp_path / "require_cross_host.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any("missing required record_id: 1004" in error for error in result.errors)


def test_gate_fails_noise_above_threshold(tmp_path: Path) -> None:
    scenario = load_correlation_expected(NOISY_SCENARIO)
    scenario.raw["expectations"]["max_noise_overcollection"] = 0
    tampered = tmp_path / "strict_noise.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert result.collected_noise_record_ids == ("1003",)
    assert any("noise overcollection" in error for error in result.errors)
    assert any("1003" in error for error in result.errors)


def test_gate_fails_missing_process_relationship(tmp_path: Path) -> None:
    scenario = load_correlation_expected(PASS_SCENARIO)
    scenario.raw["expectations"]["required_process_relationships"] = [
        {
            "parent_process_guid": "{aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa}",
            "child_process_guid": "{bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb}",
        }
    ]
    tampered = tmp_path / "missing_relationship.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any("relationship" in error for error in result.errors)


def test_gate_fails_when_required_events_missing(tmp_path: Path) -> None:
    scenario = load_correlation_expected(PASS_SCENARIO)
    scenario.raw["expectations"]["required_record_ids"] = [
        "1001",
        "1002",
        "2001",
        "missing-id",
    ]
    tampered = tmp_path / "missing_event.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any("missing required record_id" in error for error in result.errors)


def test_gate_fails_when_excluded_noise_collected(tmp_path: Path) -> None:
    scenario = load_correlation_expected(PASS_SCENARIO)
    scenario.raw["inputs"]["window_seconds"] = 7200
    tampered = tmp_path / "wide_window.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any("excluded record_id" in error for error in result.errors)


def test_gate_fails_on_manifest_checksum_mismatch(tmp_path: Path) -> None:
    bad_manifest = tmp_path / "fixture_manifest.yaml"
    bad_manifest.write_text(
        yaml.safe_dump(
            {
                "version": "1",
                "fixtures": [
                    {
                        "path": "fixtures/sysmon/process_chain.json",
                        "sha256": "0" * 64,
                        "description": "tampered",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    scenario = load_correlation_expected(PASS_SCENARIO)
    scenario.raw["inputs"]["fixture_manifest"] = str(bad_manifest)
    tampered = tmp_path / "bad_manifest_scenario.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any("manifest" in error.lower() for error in result.errors)


def test_gate_fails_when_scenario_fixture_unlisted_in_manifest(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "partial_manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "version": "1",
                "fixtures": [
                    {
                        "path": "fixtures/sysmon/process_chain.json",
                        "sha256": hashlib.sha256(
                            (
                                REPO_ROOT / "tests/fixtures/sysmon/process_chain.json"
                            ).read_bytes()
                        ).hexdigest(),
                        "description": "listed",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    scenario = load_correlation_expected(PASS_SCENARIO)
    scenario.raw["inputs"]["fixture_manifest"] = str(manifest_path)
    tampered = tmp_path / "unlisted_fixture.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any(
        "not listed in fixture manifest" in error for error in result.errors
    )


def test_gate_blocks_before_correlation_on_manifest_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def _fake_correlate(**_kwargs: object) -> object:
        calls.append("correlate")
        raise AssertionError("correlation should not run when manifest fails")

    monkeypatch.setattr("evals.correlation_gate.correlate_telemetry", _fake_correlate)

    bad_manifest = tmp_path / "fixture_manifest.yaml"
    bad_manifest.write_text(
        yaml.safe_dump(
            {
                "version": "1",
                "fixtures": [
                    {
                        "path": "fixtures/sysmon/process_chain.json",
                        "sha256": "deadbeef",
                        "description": "bad",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    scenario = load_correlation_expected(PASS_SCENARIO)
    scenario.raw["inputs"]["fixture_manifest"] = str(bad_manifest)
    tampered = tmp_path / "blocked.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert calls == []


def test_gate_fails_corroboration_when_security_dropped(tmp_path: Path) -> None:
    scenario = load_correlation_expected(PASS_SCENARIO)
    scenario.raw["inputs"]["security_fixtures"] = []
    tampered = tmp_path / "sysmon_only.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any("account corroboration failed" in error for error in result.errors)
    assert set(result.collected_record_ids) == {"1001", "1002"}


def test_gate_fails_corroboration_when_security_provenance_wrong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import praetor.correlation as correlation

    original = correlation.normalize_security_event

    def _wrong_provenance(event: object) -> object:
        fact = original(event)  # type: ignore[arg-type]
        return fact.model_copy(update={"provenance_path": "wrong_provenance"})

    monkeypatch.setattr(correlation, "normalize_security_event", _wrong_provenance)

    result = run_correlation_gate(PASS_SCENARIO, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any(
        "account corroboration failed" in error or "missing required provenance_path"
        in error
        for error in result.errors
    )
    assert "2001" in result.collected_record_ids


def test_gate_enforces_required_ambiguity_flag() -> None:
    result = run_correlation_gate(NOISY_SCENARIO, repo_root=REPO_ROOT)
    assert result.passed is True, result.errors


def test_gate_fails_when_ambiguity_flag_missing(tmp_path: Path) -> None:
    scenario = load_correlation_expected(NOISY_SCENARIO)
    scenario.raw["expectations"]["required_ambiguity_flag_record_ids"] = ["1001"]
    tampered = tmp_path / "wrong_ambiguity.yaml"
    tampered.write_text(yaml.safe_dump(scenario.raw), encoding="utf-8")

    result = run_correlation_gate(tampered, repo_root=REPO_ROOT)
    assert result.passed is False
    assert any("ambiguity_flag must be true" in error for error in result.errors)


def test_window_boundary_collected_record_ids() -> None:
    result = run_correlation_gate(WINDOW_SCENARIO, repo_root=REPO_ROOT)
    assert result.passed is True, result.errors
    assert set(result.collected_record_ids) == {"1005"}
    assert "1006" not in result.collected_record_ids


def test_correlation_gate_cli() -> None:
    from evals.correlation_gate import main

    assert main([]) == 0


def test_fixture_manifest_entry_checksums_match_repo(tmp_path: Path) -> None:
    chain = REPO_ROOT / "tests/fixtures/sysmon/process_chain.json"
    digest = hashlib.sha256(chain.read_bytes()).hexdigest()
    manifest = {
        "version": "1",
        "fixtures": [
            {
                "path": "fixtures/sysmon/process_chain.json",
                "sha256": digest,
                "description": "ok",
            }
        ],
    }
    fixtures_parent = tmp_path / "tests" / "fixtures"
    fixtures_parent.mkdir(parents=True)
    manifest_path = fixtures_parent / "fixture_manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    rel = fixtures_parent / "sysmon" / "process_chain.json"
    rel.parent.mkdir(parents=True)
    rel.write_bytes(chain.read_bytes())

    result = verify_fixture_manifest_checksums(
        manifest_path,
        repo_root=tmp_path,
        fixtures_parent=fixtures_parent,
    )
    assert result.passed is True

    rel.write_text(json.dumps({"tampered": True}), encoding="utf-8")
    result = verify_fixture_manifest_checksums(
        manifest_path,
        repo_root=tmp_path,
        fixtures_parent=fixtures_parent,
    )
    assert result.passed is False
