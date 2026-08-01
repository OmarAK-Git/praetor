"""Phase 3 regression gate (Task 31).

Combines correlation accuracy on noisy real telemetry, identity compliance
evidence, account containment prerequisites, and Phase 2 safety invariants
evaluated on Task 28 correlated ``EvidenceBundle`` output.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.correlation_gate import (
    EXPECTED_DIR,
    REPO_ROOT,
    load_correlation_expected,
    run_correlation_gate,
)
from evals.harness import (
    _persist_snapshot_with_overrides,
    allowlist_containment_policy,
    run_all_scenarios,
)
from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.config.errors import PreflightError
from praetor.config.loader import load_org_config_source
from praetor.config.preflight import run_preflight
from praetor.config.state import fetch_active_snapshot
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.correlation import correlate_telemetry, load_fixture_events
from praetor.evidence.provenance import (
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    meets_account_corroboration,
)
from praetor.policy.gate import evaluate_policy_gate
from praetor.policy.identity import (
    ACCOUNT_CONTAINMENT_DISABLED,
    INSUFFICIENT_CORROBORATION,
)
from praetor.state.store import StateStore, open_state_store

REQUIRED_EXPECTED_SCENARIO_ID = "noisy_correlated_real_telemetry"
REQUIRED_EXPECTED_PATH = EXPECTED_DIR / f"{REQUIRED_EXPECTED_SCENARIO_ID}.yaml"
INCIDENT_HOST_ID = "WORKSTATION1"
NOISE_HOST_ID = "WORKSTATION2"
IDENTITY_COMPLIANCE_TEST_PATH = (
    REPO_ROOT / "tests" / "correlation" / "test_correlator_identity_compliance.py"
)
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_org.yaml"
SOC_LEAD_TOKEN = "soc-lead-token"
FIXED_NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)


@dataclass(frozen=True)
class Phase3CheckResult:
    name: str
    passed: bool
    errors: tuple[str, ...] = ()


def _parse_anchor_time(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolve_repo_path(path_value: str, *, repo_root: Path) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def _load_fixture_events_from_paths(
    paths: Sequence[str],
    *,
    repo_root: Path,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path_value in paths:
        fixture_path = _resolve_repo_path(path_value, repo_root=repo_root)
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        events.extend(load_fixture_events(payload))
    return events


def correlate_bundle_from_expected(
    expected_path: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> EvidenceBundle:
    """Build correlated EvidenceBundle from a correlation expected scenario."""
    scenario = load_correlation_expected(expected_path)
    inputs = scenario.inputs
    anchor_time = _parse_anchor_time(str(inputs.get("anchor_time")))
    window_seconds = int(inputs.get("window_seconds", 300))
    sysmon_paths = [str(item) for item in inputs.get("sysmon_fixtures") or []]
    security_paths = [str(item) for item in inputs.get("security_fixtures") or []]
    sysmon_events = _load_fixture_events_from_paths(sysmon_paths, repo_root=repo_root)
    security_events = _load_fixture_events_from_paths(
        security_paths,
        repo_root=repo_root,
    )
    correlation = correlate_telemetry(
        sysmon_events=sysmon_events,
        security_events=security_events,
        anchor_time=anchor_time,
        window_seconds=window_seconds,
    )
    return correlation.bundle


def check_required_expected_file(
    *,
    expected_path: Path = REQUIRED_EXPECTED_PATH,
) -> Phase3CheckResult:
    if expected_path.is_file():
        return Phase3CheckResult(
            name="required_expected_file",
            passed=True,
        )
    return Phase3CheckResult(
        name="required_expected_file",
        passed=False,
        errors=(
            f"missing human-authored expected output: {expected_path}",
        ),
    )


def check_noisy_correlation_accuracy(
    *,
    expected_path: Path = REQUIRED_EXPECTED_PATH,
    repo_root: Path = REPO_ROOT,
) -> Phase3CheckResult:
    result = run_correlation_gate(expected_path, repo_root=repo_root)
    if result.passed:
        return Phase3CheckResult(name="noisy_correlation_accuracy", passed=True)
    return Phase3CheckResult(
        name="noisy_correlation_accuracy",
        passed=False,
        errors=result.errors,
    )


def check_identity_compliance_evidence(
    *,
    repo_root: Path = REPO_ROOT,
    test_path: Path = IDENTITY_COMPLIANCE_TEST_PATH,
) -> Phase3CheckResult:
    if not test_path.is_file():
        return Phase3CheckResult(
            name="identity_compliance_evidence",
            passed=False,
            errors=(f"identity compliance tests missing: {test_path}",),
        )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(test_path.relative_to(repo_root)),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return Phase3CheckResult(name="identity_compliance_evidence", passed=True)
    detail = (completed.stdout + completed.stderr).strip()
    return Phase3CheckResult(
        name="identity_compliance_evidence",
        passed=False,
        errors=(detail or "identity compliance tests failed",),
    )


def check_account_containment_prerequisite(
    *,
    repo_root: Path = REPO_ROOT,
) -> Phase3CheckResult:
    identity = check_identity_compliance_evidence(repo_root=repo_root)
    if not identity.passed:
        return Phase3CheckResult(
            name="account_containment_prerequisite",
            passed=False,
            errors=identity.errors,
        )
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    doc = dict(doc)
    doc["account_auto_contain_enabled"] = True
    try:
        run_preflight(doc, verbatim_text="phase3-gate-account-prerequisite")
    except PreflightError as exc:
        return Phase3CheckResult(
            name="account_containment_prerequisite",
            passed=False,
            errors=(
                f"account_auto_contain_enabled=true rejected at preflight: {exc.code}",
            ),
        )
    return Phase3CheckResult(
        name="account_containment_prerequisite",
        passed=True,
    )


def _auto_contain_judgment(
    bundle: EvidenceBundle,
    *,
    refs: list[CitedEvidenceRef],
) -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.AUTO_CONTAIN,
        cited_evidence_refs=refs,
        key_tells=["phase3-gate"],
        org_config_refs=["containment_policy.default_action"],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="phase3 gate",
        narrative="phase3 gate",
        model_name="phase3-gate",
        provider_name="phase3-gate",
    )


def _open_activated_store(db_path: Path) -> StateStore:
    verifier = PrincipalMapVerifier(
        {SOC_LEAD_TOKEN: Principal(identity="soc-lead-1", role="soc_lead")}
    )
    store = open_state_store(db_path)
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    return store


def check_phase2_safety_on_noisy_bundle(
    *,
    expected_path: Path = REQUIRED_EXPECTED_PATH,
    repo_root: Path = REPO_ROOT,
) -> Phase3CheckResult:
    bundle = correlate_bundle_from_expected(expected_path, repo_root=repo_root)
    errors: list[str] = []

    if not meets_account_corroboration(bundle.facts):
        errors.append(
            "noisy correlated bundle must preserve account corroboration"
        )

    paths = {fact.provenance_path for fact in bundle.facts}
    if SYSMON_EVENT_LOG not in paths or WINDOWS_SECURITY_LOG not in paths:
        errors.append("noisy correlated bundle must include Sysmon and Security facts")

    scenario = load_correlation_expected(expected_path)
    inputs = scenario.inputs
    anchor_time = _parse_anchor_time(str(inputs.get("anchor_time")))
    window_seconds = int(inputs.get("window_seconds", 300))
    sysmon_paths = [str(item) for item in inputs.get("sysmon_fixtures") or []]
    sysmon_only_events = _load_fixture_events_from_paths(sysmon_paths, repo_root=repo_root)
    sysmon_only_bundle = correlate_telemetry(
        sysmon_events=sysmon_only_events,
        security_events=[],
        anchor_time=anchor_time,
        window_seconds=window_seconds,
    ).bundle

    security_fact = next(
        (fact for fact in bundle.facts if fact.provenance_path == WINDOWS_SECURITY_LOG),
        None,
    )
    if security_fact is None:
        errors.append("missing Security fact for account gate check")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            store = _open_activated_store(Path(tmp) / "state.db")
            try:
                snapshot = fetch_active_snapshot(store.conn)
                assert snapshot is not None
                account_result = evaluate_policy_gate(
                    store.conn,
                    judgment=_auto_contain_judgment(
                        bundle,
                        refs=[
                            CitedEvidenceRef(
                                evidence_id=security_fact.evidence_id,
                                field_path="target_sid",
                            )
                        ],
                    ),
                    evidence_bundle=bundle,
                    org_snapshot=snapshot,
                    alert_identity="phase3-noisy-account-gate-off",
                    decision_id="dec-phase3-noisy-account-gate-off",
                    now=FIXED_NOW,
                )
                if account_result.final_disposition != Disposition.ESCALATE:
                    errors.append(
                        "account auto_contain proposal must escalate when gate disabled"
                    )
                if account_result.fault_flags != [ACCOUNT_CONTAINMENT_DISABLED]:
                    errors.append(
                        "account auto_contain must record account_containment_disabled"
                    )
                if account_result.system_fault_escalation is not False:
                    errors.append(
                        "account_containment_disabled must keep system_fault_escalation=false"
                    )

                host_snapshot = _persist_snapshot_with_overrides(
                    store,
                    snapshot,
                    containment_policy=allowlist_containment_policy(
                        host_ids=[INCIDENT_HOST_ID],
                    ),
                )
                sysmon_fact = next(
                    fact
                    for fact in sysmon_only_bundle.facts
                    if fact.provenance_path == SYSMON_EVENT_LOG
                    and fact.normalized_fields.get("host_id") == INCIDENT_HOST_ID
                    and not fact.ambiguity_flag
                )
                host_single_sysmon = evaluate_policy_gate(
                    store.conn,
                    judgment=_auto_contain_judgment(
                        sysmon_only_bundle,
                        refs=[
                            CitedEvidenceRef(
                                evidence_id=sysmon_fact.evidence_id,
                                field_path="host_id",
                            )
                        ],
                    ),
                    evidence_bundle=sysmon_only_bundle,
                    org_snapshot=host_snapshot,
                    alert_identity="phase3-noisy-host-single-sysmon",
                    decision_id="dec-phase3-noisy-host-single-sysmon",
                    now=FIXED_NOW,
                )
                if host_single_sysmon.final_disposition != Disposition.ESCALATE:
                    errors.append(
                        "sysmon-only bundle must escalate under DEC-066 presence "
                        "corroboration floor"
                    )
                if host_single_sysmon.fault_flags != [INSUFFICIENT_CORROBORATION]:
                    errors.append(
                        "sysmon-only host cite must record insufficient_corroboration, "
                        f"got {host_single_sysmon.fault_flags}"
                    )
                if host_single_sysmon.containment_directive is not None:
                    errors.append(
                        "sysmon-only host cite must not emit containment directive"
                    )

                incident_sysmon_facts = [
                    fact
                    for fact in sysmon_only_bundle.facts
                    if fact.provenance_path == SYSMON_EVENT_LOG
                    and fact.normalized_fields.get("host_id") == INCIDENT_HOST_ID
                    and not fact.ambiguity_flag
                ]
                if len(incident_sysmon_facts) < 2:
                    errors.append(
                        "sysmon-only bundle must include at least two non-ambiguous "
                        f"Sysmon facts for {INCIDENT_HOST_ID}"
                    )
                else:
                    enriched_bundle = EvidenceBundle(
                        facts=[
                            *sysmon_only_bundle.facts,
                            EvidenceFact(
                                evidence_id="phase3-aux-path",
                                normalized_fields={
                                    "host_id": INCIDENT_HOST_ID,
                                    "event_id": 1,
                                },
                                source_event_reference="syn:phase3:aux:1",
                                raw_source="{}",
                                provenance_path="synthetic/walking_skeleton",
                                ambiguity_flag=False,
                                timestamp=FIXED_NOW,
                            ),
                        ]
                    )
                    host_dual_path = evaluate_policy_gate(
                        store.conn,
                        judgment=_auto_contain_judgment(
                            enriched_bundle,
                            refs=[
                                CitedEvidenceRef(
                                    evidence_id=fact.evidence_id,
                                    field_path="host_id",
                                )
                                for fact in incident_sysmon_facts[:2]
                            ],
                        ),
                        evidence_bundle=enriched_bundle,
                        org_snapshot=host_snapshot,
                        alert_identity="phase3-noisy-host-dual-path",
                        decision_id="dec-phase3-noisy-host-dual-path",
                        now=FIXED_NOW,
                    )
                    if host_dual_path.final_disposition != Disposition.AUTO_CONTAIN:
                        errors.append(
                            "dual-path bundle with two cited source events must "
                            "auto_contain under DEC-066"
                        )
                    if host_dual_path.fault_flags:
                        errors.append(
                            "dual-path enriched host cite must not record fault "
                            f"flags, got {host_dual_path.fault_flags}"
                        )
                    dual_directive = host_dual_path.containment_directive
                    if dual_directive is None:
                        errors.append(
                            "dual-path host auto_contain must emit containment directive"
                        )
                    elif dual_directive.target_id != INCIDENT_HOST_ID:
                        errors.append(
                            "containment directive must target incident host "
                            f"{INCIDENT_HOST_ID}, got {dual_directive.target_id}"
                        )

                ambiguous_sysmon = next(
                    fact
                    for fact in sysmon_only_bundle.facts
                    if fact.provenance_path == SYSMON_EVENT_LOG
                    and fact.normalized_fields.get("host_id") == INCIDENT_HOST_ID
                    and fact.ambiguity_flag
                )
                host_sole_ambiguous = evaluate_policy_gate(
                    store.conn,
                    judgment=_auto_contain_judgment(
                        sysmon_only_bundle,
                        refs=[
                            CitedEvidenceRef(
                                evidence_id=ambiguous_sysmon.evidence_id,
                                field_path="host_id",
                            )
                        ],
                    ),
                    evidence_bundle=sysmon_only_bundle,
                    org_snapshot=host_snapshot,
                    alert_identity="phase3-noisy-host-sole-ambiguous",
                    decision_id="dec-phase3-noisy-host-sole-ambiguous",
                    now=FIXED_NOW,
                )
                if host_sole_ambiguous.final_disposition != Disposition.ESCALATE:
                    errors.append(
                        "sole ambiguous host cite must escalate under corroboration floor"
                    )
                if host_sole_ambiguous.fault_flags != [INSUFFICIENT_CORROBORATION]:
                    errors.append(
                        "sole ambiguous host cite must record insufficient_corroboration"
                    )
            finally:
                store.close()

    return Phase3CheckResult(
        name="phase2_safety_on_noisy_bundle",
        passed=not errors,
        errors=tuple(errors),
    )


def check_phase2_harness(*, tmp_root: Path | None = None) -> Phase3CheckResult:
    root = tmp_root or Path(tempfile.mkdtemp(prefix="phase3-harness-"))
    results = run_all_scenarios(tmp_root=root)
    failures = [result for result in results if not result.passed]
    if not failures:
        return Phase3CheckResult(name="phase2_harness", passed=True)
    errors = [
        f"{failure.scenario_id}: {'; '.join(failure.errors)}"
        for failure in failures
    ]
    return Phase3CheckResult(
        name="phase2_harness",
        passed=False,
        errors=tuple(errors),
    )


def run_phase3_gate(
    *,
    repo_root: Path = REPO_ROOT,
    expected_path: Path = REQUIRED_EXPECTED_PATH,
    include_harness: bool = True,
    include_identity_subprocess: bool = True,
    tmp_root: Path | None = None,
) -> list[Phase3CheckResult]:
    checks: list[Phase3CheckResult] = [
        check_required_expected_file(expected_path=expected_path),
    ]
    if not checks[-1].passed:
        return checks

    checks.append(
        check_noisy_correlation_accuracy(
            expected_path=expected_path,
            repo_root=repo_root,
        )
    )
    if include_identity_subprocess:
        checks.append(
            check_identity_compliance_evidence(repo_root=repo_root)
        )
    checks.append(check_account_containment_prerequisite())
    checks.append(
        check_phase2_safety_on_noisy_bundle(
            expected_path=expected_path,
            repo_root=repo_root,
        )
    )
    if include_harness:
        checks.append(check_phase2_harness(tmp_root=tmp_root))
    return checks


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    include_harness = "--skip-harness" not in args
    include_identity = "--skip-identity-subprocess" not in args
    results = run_phase3_gate(
        include_harness=include_harness,
        include_identity_subprocess=include_identity,
    )
    failed = False
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}")
        for error in result.errors:
            print(f"  - {error}")
        if not result.passed:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
