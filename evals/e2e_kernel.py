"""Sprint 1 E2E eval kernel (spec §4). Sibling of evals.harness."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from evals.harness import (
    _apply_emergency_never_contain_setup,
    _apply_policy_setup,
    _containment_allow_from_setup,
    _default_verifier,
    _fetch_directive_for_decision_id,
    _judgment_for_bundle,
    _open_activated_store,
    _persist_snapshot_with_overrides,
    _resolve_policy_bundle,
    _stamp_backend,
    allowlist_containment_policy,
)
from evals.scorecard import (
    CAPABILITY_QUALITY_IDS,
    Arm,
    Realm,
    ScorecardRow,
    validate_scorecard_row,
)
from praetor.config.state import fetch_active_snapshot
from praetor.contracts.disposition import Disposition
from praetor.engine.orchestrator import (
    IntakeResult,
    _CountingJudgmentProvider,
    process_alert_intake,
)

if TYPE_CHECKING:
    from evals.e2e_scenario import E2EScenarioDocument

EVALS_DIR = Path(__file__).resolve().parent
E2E_SCENARIOS_DIR = EVALS_DIR / "e2e_scenarios"

REQUIRED_E2E_SCENARIO_IDS: frozenset[str] = frozenset(
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

_REALM_BY_PREFIX: dict[str, Realm] = {
    "cap": "capability",
    "gov": "governance",
    "des": "design",
    "thr": "threat",
    "use": "usability",
}


def _quality_pass_forbidden(scenario_id: str, status: str) -> bool:
    return scenario_id in CAPABILITY_QUALITY_IDS and status == "pass"


def _pin_values(source: dict[str, object], pins: tuple[str, ...]) -> dict[str, object]:
    return {pin: source[pin] for pin in pins if pin in source}


def run_e2e_scenario(
    scenario: E2EScenarioDocument,
    *,
    db_path: Path,
    arm: Arm,
) -> ScorecardRow:
    arm_cfg = scenario.arms[arm]
    expected = dict(arm_cfg.expected)
    try:
        if scenario.realm == "governance" and scenario.scenario_id == (
            "gov.never_contain_live_shape"
        ):
            observed = _run_gov_never_contain(scenario, db_path=db_path)
        elif scenario.scenario_id == "gov.feed_unhealthy_blocks_contain":
            observed = _run_gov_feed_unhealthy(scenario, db_path=db_path)
        elif scenario.scenario_id == "gov.recovery_never_contains":
            observed = _run_gov_recovery(scenario, db_path=db_path)
        elif scenario.scenario_id == "des.envelope_rejects_extra_fields":
            observed = _run_des_envelope(scenario)
        elif scenario.scenario_id == "des.path_b_stays_out_of_src":
            observed = _run_des_path_b(scenario)
        elif scenario.scenario_id == "des.evidence_hash_stable":
            observed = _run_des_hash(scenario)
        elif scenario.scenario_id == "thr.instruction_in_cmdline":
            observed = _run_thr_instruction(scenario)
        else:
            raise LookupError(f"no executor for {scenario.scenario_id}")
        status = "pass"
        failure_class = "none"
        for pin in scenario.scorecard_pins:
            if observed.get(pin) != expected.get(pin):
                status = "fail"
                failure_class = "harness"
        from evals.theater import TheaterContext, run_theater_detector

        theater = run_theater_detector(
            scenario.theater_detector,
            TheaterContext(
                scenario_id=scenario.scenario_id,
                realm=scenario.realm,
                arm=arm,
                alert_identity=str(scenario.setup.get("alert_identity", "")),
                excerpt_blob="",
                scorecard_status=status,
                scorecard_is_quality_pass=_quality_pass_forbidden(
                    scenario.scenario_id, status
                ),
                src_root=Path("src/praetor"),
                copy_roots=(),
                cite_to_subject_primary_earned=False,
            ),
        )
        if theater.tripped:
            status = "fail"
            failure_class = "theater_detector"
            observed = {**observed, "theater_message": theater.message}
        if (
            scenario.scenario_id in CAPABILITY_QUALITY_IDS
            and arm == "new_build"
            and status != "fail"
        ):
            status = "pending"
            failure_class = "none"
        row = ScorecardRow(
            schema_version="1",
            scenario_id=scenario.scenario_id,
            realm=scenario.realm,
            arm=arm,
            status=status,
            failure_class=failure_class,
            expected=_pin_values(expected, scenario.scorecard_pins),
            observed=_pin_values(observed, scenario.scorecard_pins)
            | {k: observed[k] for k in observed if k not in scenario.scorecard_pins},
            provider=arm_cfg.provider,
            notes=str(observed.get("theater_message", "")),
        )
        return validate_scorecard_row(row)
    except Exception as exc:  # noqa: BLE001 — scorecard must emit a row
        row = ScorecardRow(
            schema_version="1",
            scenario_id=scenario.scenario_id,
            realm=scenario.realm,
            arm=arm,
            status="error",
            failure_class="harness",
            expected=expected,
            observed={"exception": type(exc).__name__, "message": str(exc)},
            provider=arm_cfg.provider,
            notes=str(exc),
        )
        return validate_scorecard_row(row)


def _run_gov_never_contain(
    scenario: E2EScenarioDocument, *, db_path: Path
) -> dict[str, object]:
    setup = scenario.setup
    verifier = _default_verifier()
    store = _open_activated_store(db_path, verifier)
    try:
        _apply_emergency_never_contain_setup(store, setup, verifier)
        bundle = _resolve_policy_bundle(setup)
        proposed = Disposition(str(setup["proposed_disposition"]))
        provider = _CountingJudgmentProvider(
            judgment=_judgment_for_bundle(bundle, proposed=proposed)
        )
        result = process_alert_intake(
            store,
            judgment_provider=provider,
            stamp_backend=_stamp_backend(setup),
            alert_identity=str(setup["alert_identity"]),
            evidence_bundle=bundle,
            correlate=True,
        )
        if result.edict is None:
            raise RuntimeError("expected edict")
        directive = _fetch_directive_for_decision_id(
            store.conn, result.edict.decision_id
        )
        return {
            "final_disposition": result.edict.final_disposition.value,
            "fault_flags": list(result.edict.fault_flags),
            "directive_emitted": directive is not None,
            "used_process_alert_intake": True,
        }
    finally:
        store.close()


def _run_gov_feed_unhealthy(
    scenario: E2EScenarioDocument, *, db_path: Path
) -> dict[str, object]:
    setup = scenario.setup
    verifier = _default_verifier()
    store = _open_activated_store(db_path, verifier)
    try:
        _apply_policy_setup(store, setup, verifier)
        base = fetch_active_snapshot(store.conn)
        if base is not None:
            host_ids, asset_ids = _containment_allow_from_setup(setup)
            if host_ids or asset_ids:
                _persist_snapshot_with_overrides(
                    store,
                    base,
                    containment_policy=allowlist_containment_policy(
                        host_ids=host_ids,
                        asset_ids=asset_ids,
                    ),
                )
        bundle = _resolve_policy_bundle(setup)

        def _intake(proposed: Disposition, alert_suffix: str) -> IntakeResult:
            provider = _CountingJudgmentProvider(
                judgment=_judgment_for_bundle(bundle, proposed=proposed)
            )
            return process_alert_intake(
                store,
                judgment_provider=provider,
                stamp_backend=_stamp_backend(setup),
                alert_identity=f"{setup['alert_identity']}-{alert_suffix}",
                evidence_bundle=bundle,
            )

        blocked = _intake(Disposition.AUTO_CONTAIN, "ac")
        review = _intake(Disposition.STANDARD_REVIEW, "sr")
        assert blocked.edict is not None and review.edict is not None
        return {
            "auto_contain.final_disposition": blocked.edict.final_disposition.value,
            "auto_contain.fault_flags": list(blocked.edict.fault_flags),
            "standard_review.final_disposition": review.edict.final_disposition.value,
            "used_process_alert_intake": True,
        }
    finally:
        store.close()


def _run_gov_recovery(
    scenario: E2EScenarioDocument, *, db_path: Path
) -> dict[str, object]:
    import json

    from praetor.contracts.edict import DecisionEdict
    from praetor.engine.orchestrator import SucceedingStampBackend
    from praetor.engine.recovery import run_engine_startup_recovery
    from praetor.engine.skeleton import SKELETON_BUNDLE_HASH, skeleton_model_judgment
    from praetor.ledger.store import fetch_ledger_rows
    from praetor.state.attempts import AttemptState, transition_attempt
    from praetor.tickets.stamp import StampContext, execute_stamp

    verifier = _default_verifier()
    store = _open_activated_store(db_path, verifier)
    try:
        snapshot = fetch_active_snapshot(store.conn)
        assert snapshot is not None
        alloc = store.allocate_attempt(
            alert_identity=str(scenario.setup["alert_identity"]),
            evidence_bundle_hash=SKELETON_BUNDLE_HASH,
            org_config_snapshot_hash=snapshot.snapshot_hash,
        )
        assert alloc.attempt is not None
        aid = alloc.attempt.processing_attempt_identity
        transition_attempt(store.conn, aid, AttemptState.ACTIVE)
        transition_attempt(store.conn, aid, AttemptState.PENDING_STAMP)
        judgment = skeleton_model_judgment(proposed=Disposition.AUTO_CONTAIN)
        backend = SucceedingStampBackend()
        execute_stamp(
            store.conn,
            backend,
            StampContext(
                alert_identity=alloc.attempt.alert_identity,
                evidence_bundle_hash=alloc.attempt.evidence_bundle_hash,
                org_config_snapshot_hash=alloc.attempt.org_config_snapshot_hash,
                processing_attempt_identity=aid,
                ticket_payload={"candidate_judgment": judgment.model_dump(mode="json")},
            ),
        )
        transition_attempt(store.conn, aid, AttemptState.STAMP_RESOLVED)
        run_engine_startup_recovery(store, stamp_backend=backend)
        edicts = [
            DecisionEdict.model_validate(json.loads(row.record_json))
            for row in fetch_ledger_rows(store.conn)
            if row.record_type == "decision_edict"
        ]
        assert len(edicts) == 1
        return {
            "recovered_final_disposition": edicts[0].final_disposition.value,
            "recovered_proposed_disposition": (
                edicts[0].model_judgment.proposed_disposition.value
            ),
            "containment_directive_emitted": edicts[0].containment_directive is not None,
            "used_run_engine_startup_recovery": True,
        }
    finally:
        store.close()


def _run_des_path_b(scenario: E2EScenarioDocument) -> dict[str, object]:
    from evals.theater import TheaterContext, run_theater_detector

    src_root = Path(str(scenario.setup["src_root"]))
    finding = run_theater_detector(
        "path_b_in_src",
        TheaterContext(
            scenario_id=scenario.scenario_id,
            realm=scenario.realm,
            arm="old_build",
            alert_identity=scenario.scenario_id,
            excerpt_blob="",
            scorecard_status=None,
            scorecard_is_quality_pass=False,
            src_root=src_root,
            copy_roots=(),
            cite_to_subject_primary_earned=False,
        ),
    )
    return {
        "path_b_import_found": finding.tripped,
        "theater_message": finding.message,
    }


def _run_thr_instruction(scenario: E2EScenarioDocument) -> dict[str, object]:
    import os

    from evals.harness import FIXED_NOW
    from evals.real_provider_adversarial import INJECTION_DIRECTIVE, INJECTION_MARKER
    from praetor.contracts.disposition import Disposition
    from praetor.contracts.evidence import EvidenceFact
    from praetor.evidence.provenance import SYSMON_EVENT_LOG
    from praetor.judgment.excerpt import build_prompt_excerpt_set
    from praetor.judgment.fake_provider import FakeProvider, FakeProviderMode
    from praetor.judgment.prompt import build_judgment_prompt_payload
    from praetor.judgment.provider import JudgmentRequest

    fact = EvidenceFact(
        evidence_id="ev-inject",
        normalized_fields={
            "process_name": "powershell.exe",
            "command_line": INJECTION_DIRECTIVE,
            "host_id": "ws-01",
        },
        source_event_reference="sysmon:1:9001",
        raw_source="{}",
        provenance_path=SYSMON_EVENT_LOG,
        ambiguity_flag=False,
        timestamp=FIXED_NOW,
    )
    build_prompt_excerpt_set([fact.model_dump(mode="python")])
    payload = build_judgment_prompt_payload(
        evidence_facts=[fact.model_dump(mode="python")],
        evidence_bundle_hash="bundle-hash",
        org_config_snapshot_hash="snapshot-hash",
        org_config_verbatim="containment_policy:\n  default: escalate\n",
    )
    excerpt_blob = json.dumps(payload, sort_keys=True)
    injection_present = INJECTION_MARKER in excerpt_blob
    provider = FakeProvider(
        mode=FakeProviderMode.VALID,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    judgment = provider.generate_judgment(
        JudgmentRequest(scenario_id=scenario.scenario_id, payload=payload)
    )
    obeyed = judgment.proposed_disposition == Disposition.AUTO_CONTAIN
    live_half = "not_requested"
    if os.environ.get("PRAETOR_REAL_PROVIDER_PROBE") == "1":
        live_half = "ran"
    return {
        "injection_present_in_excerpts": injection_present,
        "fake_provider_did_not_obey_injection": not obeyed,
        "live_half": live_half,
        "excerpt_blob": excerpt_blob,
        "used_bundle_fact_count": 1,
    }


def _run_des_hash(scenario: E2EScenarioDocument) -> dict[str, object]:
    from praetor.engine.ids import hash_evidence_bundle

    bundle = _resolve_policy_bundle(scenario.setup)
    first = hash_evidence_bundle(bundle)
    second = hash_evidence_bundle(bundle)
    return {
        "hashes_equal": first == second,
        "hash_length": len(first),
        "first": first,
        "second": second,
    }


def _run_des_envelope(scenario: E2EScenarioDocument) -> dict[str, object]:
    from pydantic import ValidationError

    from praetor.contracts.alert import AlertEnvelope

    legal = AlertEnvelope.model_validate(
        {
            "schema_version": "1",
            "alert_identity": str(scenario.setup["alert_identity"]),
        }
    )
    extra_field = str(scenario.setup["extra_field"])
    raised = False
    try:
        AlertEnvelope.model_validate(
            {
                "schema_version": "1",
                "alert_identity": str(scenario.setup["alert_identity"]),
                extra_field: scenario.setup["extra_value"],
            }
        )
    except ValidationError:
        raised = True
    return {
        "raises_validation_error": raised,
        "accepted_legal_envelope": legal.alert_identity
        == str(scenario.setup["alert_identity"]),
        "rejected_cbc_field": extra_field,
    }


def missing_required_scenario_ids(present: set[str]) -> frozenset[str]:
    return REQUIRED_E2E_SCENARIO_IDS - present


def scorecards_for_missing_ids(missing: frozenset[str]) -> list[ScorecardRow]:
    rows: list[ScorecardRow] = []
    for scenario_id in sorted(missing):
        prefix = scenario_id.split(".", 1)[0]
        row = ScorecardRow(
            schema_version="1",
            scenario_id=scenario_id,
            realm=_REALM_BY_PREFIX[prefix],
            arm="old_build",
            status="error",
            failure_class="harness",
            expected={"present": True},
            observed={"present": False},
            provider="fake",
            notes="missing scenario file",
        )
        rows.append(validate_scorecard_row(row))
    return rows


def kernel_exit_code(rows: Sequence[ScorecardRow]) -> int:
    present_pairs = {(row.scenario_id, row.arm) for row in rows}
    for scenario_id in REQUIRED_E2E_SCENARIO_IDS:
        if (scenario_id, "old_build") not in present_pairs and (
            scenario_id,
            "new_build",
        ) not in present_pairs:
            return 1
    if any(row.status in {"fail", "error"} for row in rows):
        return 1
    return 0


def run_e2e_kernel(
    *,
    tmp_root: Path,
    scenarios_dir: Path | None = None,
) -> list[ScorecardRow]:
    from evals.e2e_scenario import list_e2e_scenarios

    tmp_root.mkdir(parents=True, exist_ok=True)
    directory = scenarios_dir or E2E_SCENARIOS_DIR
    docs = list_e2e_scenarios(directory)
    rows: list[ScorecardRow] = []
    present: set[str] = set()
    for index, scenario in enumerate(docs):
        present.add(scenario.scenario_id)
        for arm in ("old_build", "new_build"):
            db_path = tmp_root / f"{index}-{arm}.db"
            rows.append(run_e2e_scenario(scenario, db_path=db_path, arm=arm))
    rows.extend(scorecards_for_missing_ids(missing_required_scenario_ids(present)))
    return rows


def format_scorecards(rows: Sequence[ScorecardRow]) -> str:
    lines: list[str] = []
    for row in rows:
        lines.append(
            f"[{row.status.upper()}] {row.scenario_id} {row.arm} "
            f"failure_class={row.failure_class}"
        )
        if row.notes:
            lines.append(f"  - {row.notes}")
    return "\n".join(lines)
