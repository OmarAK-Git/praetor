"""Mandatory Phase 2 eval harness (Task 26).

Loads schema-valid scenario fixtures, runs them against FakeProvider and PolicyGate
primitives, and asserts Outcome Matrix invariants from docs/contracts.md §13.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict, cast
from unittest.mock import patch

import yaml

from evals.outcome_matrix import (
    OUTCOME_MATRIX_SFE,
    collect_scenario_matrix_pairs,
)
from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier, TokenVerifier
from praetor.config.activation import activate_org_config
from praetor.config.emergency import add_emergency_never_contain
from praetor.config.snapshot import compute_snapshot_hash_from_binding
from praetor.config.state import fetch_active_snapshot, persist_org_config_snapshot
from praetor.contracts.containment import ContainmentDirective
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.contracts.org_config_sections import ContainmentPolicy, ContainmentRule
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    _CountingJudgmentProvider,
    process_alert_intake,
)
from praetor.evidence.provenance import SYSMON_EVENT_LOG, WINDOWS_SECURITY_LOG
from praetor.judgment.excerpt import MAX_PROMPT_EXCERPT_CHARS, build_prompt_excerpt_set
from praetor.judgment.fake_provider import FakeProvider, FakeProviderMode
from praetor.judgment.prompt import build_judgment_prompt_payload
from praetor.judgment.provider import JudgmentProvider, ProviderRetryPolicy
from praetor.ledger.store import fetch_ledger_rows
from praetor.metrics.events import OutcomeMatrixFaultFlag
from praetor.policy.gate import evaluate_policy_gate
from praetor.policy.state import (
    BreakerDomain,
    init_policy_state_schema,
    rate_limit_scope_key,
    set_breaker_open,
    set_rate_counter,
)
from praetor.revocation.outbox import (
    init_revocation_feed_export_schema,
    set_feed_unhealthy,
)
from praetor.state.store import StateStore, open_state_store
from praetor.tickets.stamp import StampBackendOutcome, StampBackendResult

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
SCENARIOS_DIR = EVALS_DIR / "scenarios"
SCHEMA_PATH = EVALS_DIR / "schemas" / "scenario_schema.json"
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_org.yaml"
SOC_LEAD_TOKEN = "soc-lead-token"
FIXED_NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)

OMISSION_RE = re.compile(r"\[\.\.\.omitting (?P<count>\d+) characters\]")


@dataclass(frozen=True)
class ScenarioDocument:
    schema_version: str
    scenario_id: str
    description: str
    runner: str
    setup: Mapping[str, Any]
    expectations: Mapping[str, Any]
    source_path: Path


@dataclass
class ScenarioRunResult:
    scenario_id: str
    passed: bool
    errors: list[str] = field(default_factory=list)


class _FailedStampBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        _ = stamp_id, payload
        return StampBackendResult(outcome=StampBackendOutcome.FAILED, payload={})


class _UnknownStampBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        _ = stamp_id, payload
        from praetor.tickets.stamp import StampTimeoutError

        raise StampTimeoutError("harness ambiguous stamp")


class _PendingStampBackend(_UnknownStampBackend):
    """v1 intake in-flight stamp uses non-terminal outbox status (unknown)."""


def _fetch_directive_for_decision_id(
    conn: sqlite3.Connection,
    decision_id: str,
    *,
    now: datetime | None = None,
) -> ContainmentDirective | None:
    from praetor.config.state import fetch_outstanding_unrevoked_directives

    for directive in fetch_outstanding_unrevoked_directives(conn, now=now):
        if directive.decision_id == decision_id:
            return directive
    return None


def _assert_directive_expectations(
    conn: sqlite3.Connection,
    *,
    decision_id: str,
    expectations: Mapping[str, Any],
    errors: list[str],
    now: datetime | None = None,
) -> None:
    if not expectations.get("directive_emitted"):
        return
    directive = _fetch_directive_for_decision_id(conn, decision_id, now=now)
    if directive is None:
        errors.append("expected containment directive emission")
        return
    expected_type = expectations.get("containment_target_type")
    expected_id = expectations.get("containment_target_id")
    if expected_type and directive.target_type.value != expected_type:
        errors.append(
            f"containment target_type expected {expected_type}, "
            f"got {directive.target_type.value}"
        )
    if expected_id and directive.target_id != expected_id:
        errors.append(
            f"containment target_id expected {expected_id}, got {directive.target_id}"
        )


def _load_schema() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _validate_against_schema(data: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if schema.get("type") != "object":
        return ["root schema must be object"]
    required = schema.get("required", [])
    if not isinstance(required, list):
        return ["schema required must be a list"]
    for key in required:
        if key not in data:
            errors.append(f"missing required field: {key}")
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return errors + ["schema properties must be an object"]
    for key, spec in properties.items():
        if key not in data:
            continue
        if not isinstance(spec, dict):
            continue
        if spec.get("type") == "string" and "const" in spec and data[key] != spec["const"]:
            errors.append(f"{key}: expected {spec['const']!r}, got {data[key]!r}")
        if spec.get("type") == "string" and "enum" in spec and data[key] not in spec["enum"]:
            errors.append(f"{key}: {data[key]!r} not in enum {spec['enum']}")
    if schema.get("additionalProperties") is False:
        allowed = set(properties.keys())
        extra = set(data.keys()) - allowed
        if extra:
            errors.append(f"unexpected fields: {sorted(extra)}")
    return errors


def _validate_expectations(
    *,
    runner: str,
    expectations: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []

    def _check_escalate_block(block: Mapping[str, Any], label: str) -> None:
        if str(block.get("final_disposition")) != "escalate":
            return
        for required in ("fault_flags", "system_fault_escalation"):
            if required not in block:
                errors.append(f"{label}escalate block missing {required}")

    if runner == "revocation_feed_degraded_mode":
        for key in ("auto_contain", "standard_review"):
            block = expectations.get(key)
            if isinstance(block, Mapping):
                _check_escalate_block(block, f"{key}: ")
    else:
        _check_escalate_block(expectations, "")

    for flag, _sfe in collect_scenario_matrix_pairs(
        runner=runner, expectations=expectations
    ):
        try:
            OutcomeMatrixFaultFlag(flag)
        except ValueError:
            errors.append(f"unknown Outcome Matrix fault flag: {flag!r}")
            continue
        expected_sfe = OUTCOME_MATRIX_SFE[OutcomeMatrixFaultFlag(flag)]
        # pairs only include escalate rows; SFE checked at runtime in _assert_outcome
        _ = expected_sfe

    _RUNNER_EXPECTATION_KEYS: dict[str, frozenset[str]] = {
        "engine_intake": frozenset(
            {
                "final_disposition",
                "fault_flags",
                "system_fault_escalation",
                "judgment_provider_calls",
                "no_policy_override",
                "candidate_disposition_preserved",
                "proposed_disposition",
                "directive_emitted",
                "containment_target_type",
                "containment_target_id",
            }
        ),
        "policy_gate": frozenset(
            {
                "final_disposition",
                "fault_flags",
                "system_fault_escalation",
                "directive_emitted",
                "containment_target_type",
                "containment_target_id",
                "idempotency_suppressed_on_repeat",
                "ledger_record_type",
            }
        ),
        "duplicate_retry": frozenset(
            {
                "second_intake_edict_none",
                "ledger_edict_count_unchanged",
            }
        ),
        "prompt_isolation": frozenset(
            {
                "raw_source_excluded",
                "excerpt_max_chars",
            }
        ),
        "revocation_feed_degraded_mode": frozenset(
            {
                "auto_contain",
                "standard_review",
            }
        ),
    }
    _ALL_EXPECTATION_KEYS = frozenset().union(*_RUNNER_EXPECTATION_KEYS.values())
    consumed = _RUNNER_EXPECTATION_KEYS.get(runner)
    if consumed is None:
        errors.append(f"unknown runner for expectation validation: {runner!r}")
    else:
        for key in expectations:
            if key not in _ALL_EXPECTATION_KEYS:
                errors.append(f"unknown expectation key: {key!r}")
            elif key not in consumed:
                errors.append(
                    f"expectation key {key!r} is not consumed by runner {runner!r}"
                )

    return errors


def load_scenario(path: Path) -> ScenarioDocument:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"{path.name}: scenario root must be a mapping"
        raise ValueError(msg)
    schema = _load_schema()
    errors = _validate_against_schema(raw, schema)
    runner = str(raw.get("runner", ""))
    expectations = raw.get("expectations", {})
    if isinstance(expectations, Mapping):
        errors.extend(
            _validate_expectations(runner=runner, expectations=expectations)
        )
    if errors:
        joined = "; ".join(errors)
        msg = f"{path.name}: schema validation failed: {joined}"
        raise ValueError(msg)
    scenario_id = str(raw["scenario_id"])
    if path.stem != scenario_id:
        msg = f"{path.name}: filename stem must match scenario_id {scenario_id!r}"
        raise ValueError(msg)
    return ScenarioDocument(
        schema_version=str(raw["schema_version"]),
        scenario_id=scenario_id,
        description=str(raw["description"]),
        runner=runner,
        setup=raw.get("setup", {}),
        expectations=expectations if isinstance(expectations, Mapping) else {},
        source_path=path,
    )


def list_mandatory_scenarios() -> list[ScenarioDocument]:
    paths = sorted(SCENARIOS_DIR.glob("*.yaml"))
    if not paths:
        msg = f"no scenario fixtures under {SCENARIOS_DIR}"
        raise FileNotFoundError(msg)
    return [load_scenario(path) for path in paths]


def _default_verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {SOC_LEAD_TOKEN: Principal(identity="soc-lead-1", role="soc_lead")}
    )


def _open_activated_store(db_path: Path, verifier: TokenVerifier | None = None) -> StateStore:
    store = open_state_store(db_path)
    activate_org_config(
        store,
        EXAMPLE_CONFIG,
        token=SOC_LEAD_TOKEN,
        verifier=verifier or _default_verifier(),
    )
    return store


def _disposition(value: str) -> Disposition:
    return Disposition(value)


def _citable_field_path(fact: EvidenceFact) -> str:
    for key in ("process_name", "host_id", "target_sid", "account_name"):
        if key in fact.normalized_fields:
            return key
    return "process_name"


def _host_bundle(*, host_id: str = "ws-01") -> EvidenceBundle:
    return EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="ev-host-sysmon",
                normalized_fields={"host_id": host_id, "process_name": "cmd.exe"},
                source_event_reference="syn:host:sysmon:1",
                raw_source="{}",
                provenance_path=SYSMON_EVENT_LOG,
                ambiguity_flag=False,
                timestamp=FIXED_NOW,
            ),
            EvidenceFact(
                evidence_id="ev-host-security",
                normalized_fields={"host_id": host_id, "event_id": 4624},
                source_event_reference="syn:host:security:1",
                raw_source="{}",
                provenance_path=WINDOWS_SECURITY_LOG,
                ambiguity_flag=False,
                timestamp=FIXED_NOW,
            ),
        ]
    )


def _default_auto_contain_citation_refs(
    bundle: EvidenceBundle,
) -> list[CitedEvidenceRef]:
    sysmon = next(
        (fact for fact in bundle.facts if fact.provenance_path == SYSMON_EVENT_LOG),
        None,
    )
    security = next(
        (
            fact
            for fact in bundle.facts
            if fact.provenance_path == WINDOWS_SECURITY_LOG
        ),
        None,
    )
    if sysmon is not None and security is not None:
        return [
            CitedEvidenceRef(
                evidence_id=sysmon.evidence_id,
                field_path=_citable_field_path(sysmon),
            ),
            CitedEvidenceRef(
                evidence_id=security.evidence_id,
                field_path=_citable_field_path(security),
            ),
        ]
    return [
        CitedEvidenceRef(
            evidence_id=bundle.facts[0].evidence_id,
            field_path=_citable_field_path(bundle.facts[0]),
        )
    ]


def _incomplete_account_bundle() -> EvidenceBundle:
    return EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="syn-ev-sysmon",
                normalized_fields={
                    "process_name": "powershell.exe",
                    "user": "CORP\\jdoe",
                },
                source_event_reference="sysmon:1:1001",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=FIXED_NOW,
            )
        ]
    )


def _bundle_from_synthetic_fixture(relative_path: str) -> EvidenceBundle:
    path = REPO_ROOT / relative_path
    data = json.loads(path.read_text(encoding="utf-8"))
    facts = [EvidenceFact.model_validate(item) for item in data["facts"]]
    return EvidenceBundle(facts=facts)


def _judgment_for_bundle(
    bundle: EvidenceBundle,
    *,
    proposed: Disposition,
    cited_refs: list[CitedEvidenceRef] | None = None,
) -> ModelJudgment:
    if cited_refs is None:
        cited_refs = _default_auto_contain_citation_refs(bundle)
    return ModelJudgment(
        proposed_disposition=proposed,
        cited_evidence_refs=cited_refs,
        key_tells=["eval"],
        org_config_refs=["containment_policy.default_escalate"],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="eval",
        narrative="eval",
        model_name="fake",
        provider_name="fake",
    )


def _provider_mode(name: str) -> FakeProviderMode:
    return FakeProviderMode(name)


def _stamp_backend(
    setup: Mapping[str, Any],
) -> (
    SucceedingStampBackend
    | _FailedStampBackend
    | _UnknownStampBackend
    | _PendingStampBackend
):
    backend = setup.get("stamp_backend", "succeeding")
    if backend == "failed":
        return _FailedStampBackend()
    if backend == "unknown":
        return _UnknownStampBackend()
    if backend == "pending":
        return _PendingStampBackend()
    return SucceedingStampBackend()


def _persist_snapshot_with_overrides(
    store: StateStore,
    base: OrgConfigSnapshot,
    **overrides: object,
) -> OrgConfigSnapshot:
    payload = base.model_dump(mode="json")
    for key, value in overrides.items():
        if hasattr(value, "model_dump"):
            payload[key] = value.model_dump(mode="json")
        else:
            payload[key] = value
    payload.pop("snapshot_hash", None)
    snapshot_hash = compute_snapshot_hash_from_binding(payload)
    updated = OrgConfigSnapshot.model_validate(
        {**payload, "snapshot_hash": snapshot_hash}
    )
    persist_org_config_snapshot(store.conn, updated, verbatim_render_text="eval-policy")
    store.conn.execute(
        """
        UPDATE active_org_config
        SET snapshot_hash = ?, verbatim_render_id = ?
        WHERE id = 1
        """,
        (updated.snapshot_hash, "eval-policy-render"),
    )
    store.conn.commit()
    return updated


def _permissive_containment_policy() -> ContainmentPolicy:
    return ContainmentPolicy(
        rules=[
            ContainmentRule(
                name="allow_hosts",
                action="auto_contain",
                scope={"catch_all": True},
            ),
        ],
    )


def _maybe_apply_permissive_containment(
    store: StateStore,
    base: OrgConfigSnapshot,
    *,
    proposed_disposition: str,
    preconditions: Mapping[str, Any] | None,
) -> OrgConfigSnapshot | None:
    if proposed_disposition != Disposition.AUTO_CONTAIN.value:
        return None
    if isinstance(preconditions, Mapping):
        if preconditions.get("conflicting_containment_rules"):
            return None
        if preconditions.get("containment_policy_blocks"):
            return None
    return _persist_snapshot_with_overrides(
        store,
        base,
        containment_policy=_permissive_containment_policy(),
    )


def _assert_outcome(
    *,
    final_disposition: Disposition,
    fault_flags: Sequence[str],
    system_fault_escalation: bool,
    expectations: Mapping[str, Any],
    errors: list[str],
    prefix: str = "",
) -> None:
    label = f"{prefix}: " if prefix else ""
    expected_final = _disposition(str(expectations["final_disposition"]))
    if final_disposition != expected_final:
        errors.append(
            f"{label}final_disposition expected {expected_final.value}, "
            f"got {final_disposition.value}"
        )
    expected_flags = list(expectations.get("fault_flags", []))
    if list(fault_flags) != expected_flags:
        errors.append(
            f"{label}fault_flags expected {expected_flags}, got {list(fault_flags)}"
        )
    if expected_final == Disposition.ESCALATE:
        if "system_fault_escalation" not in expectations:
            errors.append(
                f"{label}escalate outcome requires system_fault_escalation in expectations"
            )
        else:
            expected_sfe = bool(expectations["system_fault_escalation"])
            if system_fault_escalation != expected_sfe:
                errors.append(
                    f"{label}system_fault_escalation expected {expected_sfe}, "
                    f"got {system_fault_escalation}"
                )
    elif "system_fault_escalation" in expectations:
        expected_sfe = bool(expectations["system_fault_escalation"])
        if system_fault_escalation != expected_sfe:
            errors.append(
                f"{label}system_fault_escalation expected {expected_sfe}, "
                f"got {system_fault_escalation}"
            )


def _prompt_isolation_facts() -> list[dict[str, Any]]:
    long_command = "head-" + ("A" * 120) + "-middle-" + ("B" * 120) + "-tail"
    return [
        {
            "evidence_id": "ev-1",
            "normalized_fields": {
                "process_name": "powershell.exe",
                "command_line": long_command,
                "raw_source": "normalized raw source must not leak",
                "details": {
                    "safe": "retained",
                    "raw_source": "nested raw source must not leak",
                },
            },
            "source_event_reference": "sysmon:1",
            "raw_source": "DO-NOT-LEAK raw event body with instructions",
            "provenance_path": "sysmon_event_log",
            "ambiguity_flag": False,
        },
        {
            "evidence_id": "ev-2",
            "normalized_fields": {"unicode_payload": "π" * 260},
            "source_event_reference": "security:2",
            "raw_source": "another raw source that must stay isolated",
            "provenance_path": "windows_security_log",
            "ambiguity_flag": True,
        },
    ]


def _serialized_prompt_value(value: Any) -> str:
    if isinstance(value, Mapping):
        return json.dumps(
            {key: _serialized_prompt_value(item) for key, item in value.items()},
            sort_keys=True,
        )
    if isinstance(value, list):
        return json.dumps([_serialized_prompt_value(item) for item in value], sort_keys=True)
    return json.dumps(value, sort_keys=True)


def _run_engine_intake(
    scenario: ScenarioDocument,
    store: StateStore,
    errors: list[str],
) -> None:
    setup = scenario.setup
    expectations = scenario.expectations
    base = fetch_active_snapshot(store.conn)
    if base is not None:
        proposed_name = str(
            setup.get(
                "proposed_disposition",
                setup.get("provider_proposed_disposition", "standard_review"),
            )
        )
        wants_auto_contain = (
            proposed_name == Disposition.AUTO_CONTAIN.value
            or expectations.get("final_disposition") == Disposition.AUTO_CONTAIN.value
        )
        if wants_auto_contain:
            preconditions = setup.get("policy_preconditions", {})
            _maybe_apply_permissive_containment(
                store,
                base,
                proposed_disposition=Disposition.AUTO_CONTAIN.value,
                preconditions=preconditions if isinstance(preconditions, Mapping) else None,
            )
    alert_identity = str(setup.get("alert_identity", scenario.scenario_id))
    kwargs: dict[str, Any] = {
        "alert_identity": alert_identity,
        "correlate": bool(setup.get("correlate", True)),
        "enforce_config_budget": bool(setup.get("enforce_config_budget", True)),
    }

    if "bundle" in setup or "host_id" in setup:
        bundle = _resolve_policy_bundle(setup)
        proposed_name = str(
            setup.get(
                "proposed_disposition",
                setup.get("provider_proposed_disposition", "standard_review"),
            )
        )
        proposed = _disposition(proposed_name)
        provider: JudgmentProvider = _CountingJudgmentProvider(
            judgment=_judgment_for_bundle(bundle, proposed=proposed)
        )
        kwargs["evidence_bundle"] = bundle
    else:
        provider_mode_name = str(setup.get("provider_mode", "valid"))
        proposed_name = str(setup.get("provider_proposed_disposition", "standard_review"))
        provider = FakeProvider(
            mode=_provider_mode(provider_mode_name),
            proposed_disposition=_disposition(proposed_name),
        )

    retry = None
    if str(setup.get("provider_mode", "valid")) == "timeout":
        retry = ProviderRetryPolicy(max_attempts=2, backoff_seconds=0.0)
    kwargs["provider_retry_policy"] = retry

    stamp_backend = _stamp_backend(setup)
    if setup.get("config_over_budget"):
        huge = "x" * 500_000
        with patch(
            "praetor.engine.orchestrator.fetch_verbatim_render_text",
            return_value=huge,
        ):
            result = process_alert_intake(
                store,
                judgment_provider=provider,
                stamp_backend=stamp_backend,
                **kwargs,
            )
    else:
        result = process_alert_intake(
            store,
            judgment_provider=provider,
            stamp_backend=stamp_backend,
            **kwargs,
        )

    if "judgment_provider_calls" in expectations:
        expected_calls = int(expectations["judgment_provider_calls"])
        actual_calls = getattr(provider, "calls", 0)
        if actual_calls != expected_calls:
            errors.append(
                f"judgment_provider_calls expected {expected_calls}, got {actual_calls}"
            )

    if expectations.get("no_policy_override"):
        if result.edict is None:
            errors.append("expected edict for no_policy_override check")
            return
        if result.edict.policy_gate_result.proposed_disposition != result.edict.final_disposition:
            errors.append("policy override detected on benign path")
        if result.edict.fault_flags:
            errors.append(f"unexpected fault flags on benign path: {result.edict.fault_flags}")

    if expectations.get("candidate_disposition_preserved"):
        if result.edict is None:
            errors.append("expected edict for candidate_disposition_preserved check")
            return
        proposed = _disposition(str(expectations.get("proposed_disposition", "standard_review")))
        if result.edict.final_disposition != proposed:
            errors.append(
                "ticket_stamp_failed must preserve candidate final_disposition "
                f"(expected {proposed.value}, got {result.edict.final_disposition.value})"
            )

    if result.edict is None:
        errors.append("expected decision edict")
        return

    _assert_directive_expectations(
        store.conn,
        decision_id=result.edict.decision_id,
        expectations=expectations,
        errors=errors,
    )

    _assert_outcome(
        final_disposition=result.edict.final_disposition,
        fault_flags=result.edict.fault_flags,
        system_fault_escalation=result.edict.system_fault_escalation,
        expectations=expectations,
        errors=errors,
    )


def _resolve_policy_bundle(setup: Mapping[str, Any]) -> EvidenceBundle:
    bundle_type = setup.get("bundle", "host")
    if bundle_type == "host":
        return _host_bundle(host_id=str(setup.get("host_id", "ws-01")))
    if bundle_type == "incomplete_account":
        return _incomplete_account_bundle()
    if bundle_type == "synthetic_fixture":
        return _bundle_from_synthetic_fixture(str(setup["synthetic_fixture"]))
    msg = f"unsupported bundle type: {bundle_type!r}"
    raise ValueError(msg)


def _apply_policy_setup(store: StateStore, setup: Mapping[str, Any], verifier: TokenVerifier) -> OrgConfigSnapshot | None:
    snapshot_override: OrgConfigSnapshot | None = None
    base = fetch_active_snapshot(store.conn)
    if base is None:
        return None

    preconditions = setup.get("policy_preconditions", {})
    if isinstance(preconditions, Mapping) and preconditions.get("conflicting_containment_rules"):
        policy = ContainmentPolicy(
            rules=[
                ContainmentRule.model_validate(
                    {
                        "name": "host_allow",
                        "action": "auto_contain",
                        "scope": {"target_type": "host", "target_id": "ws-01"},
                    }
                ),
                ContainmentRule.model_validate(
                    {
                        "name": "host_deny",
                        "action": "escalate",
                        "scope": {"target_type": "host", "target_id": "ws-01"},
                    }
                ),
            ],
            precedence=None,
        )
        snapshot_override = _persist_snapshot_with_overrides(
            store, base, containment_policy=policy
        )

    if isinstance(preconditions, Mapping) and preconditions.get("deny_only_rule"):
        host_id = str(setup.get("host_id", "ws-01"))
        deny_policy = ContainmentPolicy(
            rules=[
                ContainmentRule(
                    name="host_deny",
                    action="deny",
                    scope={"target_type": "host", "target_id": host_id},
                ),
            ],
        )
        snapshot_override = _persist_snapshot_with_overrides(
            store, base, containment_policy=deny_policy
        )

    emergency = setup.get("emergency_never_contain")
    if isinstance(emergency, dict):
        add_emergency_never_contain(
            store,
            token=SOC_LEAD_TOKEN,
            verifier=verifier,
            target_specification={
                "target_type": emergency["target_type"],
                "target_id": emergency["target_id"],
            },
            lifetime_seconds=int(emergency.get("lifetime_seconds", 3600)),
            audit_reason=str(emergency.get("audit_reason", "eval")),
        )
    if setup.get("feed_unhealthy"):
        init_revocation_feed_export_schema(store.conn)
        set_feed_unhealthy(store.conn, unhealthy=True)
        store.conn.commit()

    if isinstance(preconditions, Mapping):
        init_policy_state_schema(store.conn)
        host_id = str(setup.get("host_id", "ws-01"))
        if preconditions.get("rate_limit_exhausted"):
            scope_key = rate_limit_scope_key("per_host", target_type="host", target_id=host_id)
            set_rate_counter(store.conn, scope_key, 1)
            store.conn.commit()
        if preconditions.get("containment_breaker_open"):
            set_breaker_open(store.conn, BreakerDomain.CONTAINMENT, open_=True)
            store.conn.execute(
                """
                UPDATE circuit_breaker_state
                SET window_started_at = ?
                WHERE domain = ?
                """,
                (FIXED_NOW.isoformat(), BreakerDomain.CONTAINMENT.value),
            )
            store.conn.commit()

    proposed = str(setup.get("proposed_disposition", ""))
    permissive = _maybe_apply_permissive_containment(
        store,
        base,
        proposed_disposition=proposed,
        preconditions=preconditions if isinstance(preconditions, Mapping) else None,
    )
    if permissive is not None:
        snapshot_override = permissive

    return snapshot_override


class PolicyGateKwargs(TypedDict, total=False):
    provider_health_breaker_open: bool
    latency_sla_exceeded: bool
    queue_aging_exceeded: bool


def _policy_gate_kwargs(setup: Mapping[str, Any]) -> PolicyGateKwargs:
    raw = setup.get("policy_gate_kwargs", {})
    if not isinstance(raw, Mapping):
        return {}
    allowed = (
        "provider_health_breaker_open",
        "latency_sla_exceeded",
        "queue_aging_exceeded",
    )
    kwargs: PolicyGateKwargs = {}
    for key in allowed:
        if key in raw:
            kwargs[key] = bool(raw[key])  # type: ignore[literal-required]
    return kwargs


def _run_policy_gate(
    scenario: ScenarioDocument,
    store: StateStore,
    verifier: TokenVerifier,
    errors: list[str],
) -> None:
    setup = scenario.setup
    expectations = scenario.expectations
    snapshot_override = _apply_policy_setup(store, setup, verifier)

    snapshot = snapshot_override or fetch_active_snapshot(store.conn)
    if snapshot is None:
        errors.append("active org snapshot required")
        return

    bundle = _resolve_policy_bundle(setup)
    proposed = _disposition(str(setup.get("proposed_disposition", "auto_contain")))
    custom_refs = setup.get("citation_refs")
    if custom_refs is None:
        custom_refs = setup.get("invalid_citation_refs")
    if isinstance(custom_refs, list):
        refs = [
            CitedEvidenceRef(
                evidence_id=str(item["evidence_id"]),
                field_path=str(item["field_path"]),
            )
            for item in custom_refs
        ]
        judgment = _judgment_for_bundle(bundle, proposed=proposed, cited_refs=refs)
    else:
        judgment = _judgment_for_bundle(bundle, proposed=proposed)
    alert_identity = str(setup.get("alert_identity", scenario.scenario_id))
    decision_id = str(setup.get("decision_id", f"dec-{scenario.scenario_id}"))
    gate_kwargs = _policy_gate_kwargs(setup)

    result = evaluate_policy_gate(
        store.conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=snapshot,
        alert_identity=alert_identity,
        decision_id=decision_id,
        now=FIXED_NOW,
        **gate_kwargs,
    )

    _assert_outcome(
        final_disposition=result.final_disposition,
        fault_flags=result.fault_flags,
        system_fault_escalation=result.system_fault_escalation,
        expectations=expectations,
        errors=errors,
    )

    if expectations.get("directive_emitted"):
        if result.containment_directive is None:
            errors.append("expected containment directive emission")
        else:
            _assert_directive_expectations(
                store.conn,
                decision_id=decision_id,
                expectations=expectations,
                errors=errors,
                now=FIXED_NOW,
            )

    if expectations.get("idempotency_suppressed_on_repeat"):
        if result.containment_directive is None:
            errors.append("first evaluation must emit a containment directive")
            return
        first_directive_id = result.containment_directive.directive_id
        count_before = store.conn.execute(
            "SELECT COUNT(*) AS c FROM outstanding_containment_directives"
        ).fetchone()
        assert count_before is not None
        rows_before = int(count_before["c"])

        repeat = evaluate_policy_gate(
            store.conn,
            judgment=judgment,
            evidence_bundle=bundle,
            org_snapshot=snapshot,
            alert_identity=alert_identity,
            decision_id=f"{decision_id}-repeat",
            now=FIXED_NOW,
            **gate_kwargs,
        )
        if not repeat.directive_suppressed:
            errors.append("repeat evaluation must set directive_suppressed")
        if repeat.containment_directive is None:
            errors.append("repeat evaluation must return existing directive")
        elif repeat.containment_directive.directive_id != first_directive_id:
            errors.append(
                f"idempotency must return same directive_id "
                f"(expected {first_directive_id}, got {repeat.containment_directive.directive_id})"
            )
        count_after = store.conn.execute(
            "SELECT COUNT(*) AS c FROM outstanding_containment_directives"
        ).fetchone()
        assert count_after is not None
        if int(count_after["c"]) != rows_before:
            errors.append("idempotency repeat must not add outstanding_containment_directives row")

    ledger_type = expectations.get("ledger_record_type")
    if ledger_type:
        count = sum(
            1 for row in fetch_ledger_rows(store.conn) if row.record_type == ledger_type
        )
        if count < 1:
            errors.append(f"expected ledger record_type {ledger_type!r}")


def _run_prompt_isolation(scenario: ScenarioDocument, errors: list[str]) -> None:
    expectations = scenario.expectations
    facts = _prompt_isolation_facts()
    excerpt_set = build_prompt_excerpt_set(facts)
    payload = build_judgment_prompt_payload(
        evidence_facts=facts,
        evidence_bundle_hash="bundle-hash",
        org_config_snapshot_hash="snapshot-hash",
        org_config_verbatim="containment_policy:\n  default: escalate\n",
    )

    serialized = _serialized_prompt_value(payload)
    if expectations.get("raw_source_excluded", True):
        if "raw_source" in serialized:
            errors.append("raw_source leaked into prompt payload")
        for leak in (
            "DO-NOT-LEAK",
            "normalized raw source",
            "nested raw source",
            "another raw source",
        ):
            if leak in serialized:
                errors.append(f"prompt leak detected: {leak!r}")

    max_chars = int(expectations.get("excerpt_max_chars", MAX_PROMPT_EXCERPT_CHARS))
    for fact in excerpt_set.facts:
        for excerpt in fact.excerpts:
            if len(excerpt.text) > max_chars:
                errors.append(
                    f"excerpt for {excerpt.field_path} exceeds {max_chars} chars"
                )

    command_excerpt = next(
        (
            excerpt
            for fact in excerpt_set.facts
            for excerpt in fact.excerpts
            if excerpt.field_path == "normalized_fields.command_line"
        ),
        None,
    )
    if command_excerpt is None:
        errors.append("missing command_line excerpt")
    else:
        marker = OMISSION_RE.search(command_excerpt.text)
        if marker is None:
            errors.append("truncated excerpt missing omission marker")
        elif not command_excerpt.incomplete:
            errors.append("long command_line excerpt must be incomplete")


def _run_duplicate_retry(
    scenario: ScenarioDocument,
    store: StateStore,
    errors: list[str],
) -> None:
    setup = scenario.setup
    expectations = scenario.expectations
    alert_identity = str(setup.get("alert_identity", scenario.scenario_id))
    provider = FakeProvider(mode=FakeProviderMode.VALID)
    stamp_backend = SucceedingStampBackend()

    first = process_alert_intake(
        store,
        judgment_provider=provider,
        stamp_backend=stamp_backend,
        alert_identity=alert_identity,
    )
    if first.edict is None or first.decision_id is None:
        errors.append("first intake must produce edict and decision_id")
        return

    edict_count = sum(
        1 for row in fetch_ledger_rows(store.conn) if row.record_type == "decision_edict"
    )

    second = process_alert_intake(
        store,
        judgment_provider=provider,
        stamp_backend=stamp_backend,
        alert_identity=alert_identity,
    )

    if expectations.get("second_intake_edict_none", True) and second.edict is not None:
        errors.append("duplicate retry must not append a second edict")
    if second.decision_id != first.decision_id:
        errors.append(
            f"duplicate retry decision_id expected {first.decision_id}, "
            f"got {second.decision_id}"
        )

    edict_count_after = sum(
        1 for row in fetch_ledger_rows(store.conn) if row.record_type == "decision_edict"
    )
    if expectations.get("ledger_edict_count_unchanged", True):
        if edict_count_after != edict_count:
            errors.append("duplicate retry changed ledger edict count")


def _run_revocation_feed_degraded_mode(
    scenario: ScenarioDocument,
    store: StateStore,
    verifier: TokenVerifier,
    errors: list[str],
) -> None:
    setup = scenario.setup
    expectations = scenario.expectations
    _apply_policy_setup(store, setup, verifier)

    snapshot = fetch_active_snapshot(store.conn)
    if snapshot is None:
        errors.append("active org snapshot required")
        return

    auto_expect = expectations.get("auto_contain")
    if isinstance(auto_expect, dict):
        base = snapshot
        snapshot = _persist_snapshot_with_overrides(
            store,
            base,
            containment_policy=_permissive_containment_policy(),
        )
        bundle = _host_bundle(host_id=str(setup.get("host_id", "ws-01")))
        judgment = _judgment_for_bundle(bundle, proposed=Disposition.AUTO_CONTAIN)
        blocked = evaluate_policy_gate(
            store.conn,
            judgment=judgment,
            evidence_bundle=bundle,
            org_snapshot=snapshot,
            alert_identity=f"{scenario.scenario_id}-autocontain",
            decision_id=f"dec-{scenario.scenario_id}-autocontain",
            now=FIXED_NOW,
        )
        _assert_outcome(
            final_disposition=blocked.final_disposition,
            fault_flags=blocked.fault_flags,
            system_fault_escalation=blocked.system_fault_escalation,
            expectations=auto_expect,
            errors=errors,
            prefix="auto_contain",
        )
        if OutcomeMatrixFaultFlag.REVOCATION_FEED_UNHEALTHY.value not in blocked.fault_flags:
            errors.append("auto_contain path must record revocation_feed_unhealthy")

    review_expect = expectations.get("standard_review")
    if isinstance(review_expect, dict):
        bundle = _host_bundle(host_id="ws-02")
        judgment = _judgment_for_bundle(bundle, proposed=Disposition.STANDARD_REVIEW)
        allowed = evaluate_policy_gate(
            store.conn,
            judgment=judgment,
            evidence_bundle=bundle,
            org_snapshot=snapshot,
            alert_identity=f"{scenario.scenario_id}-review",
            decision_id=f"dec-{scenario.scenario_id}-review",
            now=FIXED_NOW,
        )
        _assert_outcome(
            final_disposition=allowed.final_disposition,
            fault_flags=allowed.fault_flags,
            system_fault_escalation=allowed.system_fault_escalation,
            expectations=review_expect,
            errors=errors,
            prefix="standard_review",
        )


def run_scenario(
    scenario: ScenarioDocument,
    *,
    db_path: Path,
    verifier: TokenVerifier | None = None,
) -> ScenarioRunResult:
    errors: list[str] = []
    resolved_verifier = verifier or _default_verifier()
    store = _open_activated_store(db_path, resolved_verifier)
    try:
        if scenario.runner == "engine_intake":
            _run_engine_intake(scenario, store, errors)
        elif scenario.runner == "policy_gate":
            _run_policy_gate(scenario, store, resolved_verifier, errors)
        elif scenario.runner == "prompt_isolation":
            _run_prompt_isolation(scenario, errors)
        elif scenario.runner == "duplicate_retry":
            _run_duplicate_retry(scenario, store, errors)
        elif scenario.runner == "revocation_feed_degraded_mode":
            _run_revocation_feed_degraded_mode(
                scenario, store, resolved_verifier, errors
            )
        else:
            errors.append(f"unsupported runner: {scenario.runner}")
    finally:
        store.close()
    return ScenarioRunResult(
        scenario_id=scenario.scenario_id,
        passed=not errors,
        errors=errors,
    )


def run_all_scenarios(*, tmp_root: Path) -> list[ScenarioRunResult]:
    results: list[ScenarioRunResult] = []
    for index, scenario in enumerate(list_mandatory_scenarios()):
        db_path = tmp_root / f"eval-{index}.db"
        results.append(run_scenario(scenario, db_path=db_path))
    return results


def format_results(results: Sequence[ScenarioRunResult]) -> str:
    lines: list[str] = []
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"[{status}] {result.scenario_id}")
        for error in result.errors:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    import tempfile

    with tempfile.TemporaryDirectory(prefix="praetor-eval-") as tmp:
        results = run_all_scenarios(tmp_root=Path(tmp))
    print(format_results(results))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
