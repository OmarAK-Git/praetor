"""Shared Praetor walkthrough scenarios.

Single source of truth for the interactive notebook picker, the static demo
page under ``demo/``, and the notebook CI sweep. Each scenario boots a fresh
throwaway SQLite store, activates ``configs/example_org.yaml``, wires exactly
one precondition, and exercises the real engine downstream of a scripted
judgment provider and ticket stamp.
"""

from __future__ import annotations

import contextlib
import copy
import io
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from praetor.annotations.store import init_annotation_schema, submit_annotation
from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.codification.statute_curation import (
    SourceAnnotationRef,
    StatuteEdit,
    build_proposed_statute_artifact,
    render_proposed_statute_yaml,
)
from praetor.config.activation import activate_org_config
from praetor.config.emergency import add_emergency_never_contain
from praetor.config.errors import PreflightError
from praetor.config.loader import load_org_config_source
from praetor.config.preflight import run_preflight
from praetor.config.snapshot import compute_snapshot_hash_from_binding
from praetor.config.state import (
    fetch_active_snapshot,
    fetch_outstanding_unrevoked_directives,
    persist_org_config_snapshot,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.contracts.org_config_sections import ContainmentPolicy, ContainmentRule
from praetor.engine import process_alert_intake
from praetor.judgment.prompt import build_judgment_prompt_payload_with_similar_cases
from praetor.judgment.provider import JudgmentRequest, ProviderProbeResult
from praetor.metrics.evaluations import (
    init_policy_gate_evaluation_schema,
    record_policy_gate_evaluation,
)
from praetor.policy.state import (
    BreakerDomain,
    rate_limit_scope_key,
    set_breaker_open,
    set_rate_counter,
)
from praetor.reporting.progressive_authorization import (
    build_progressive_authorization_report,
)
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import open_state_store
from praetor.tickets.stamp import StampBackendOutcome, StampBackendResult

SOC_TOKEN = "soc-lead-token"
ANALYST_TOKEN = "analyst-token"
VERIFIER = PrincipalMapVerifier(
    {
        SOC_TOKEN: Principal(identity="soc-lead-1", role="soc_lead"),
        ANALYST_TOKEN: Principal(identity="analyst-1", role="analyst"),
    }
)


def find_repo_root() -> Path:
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents):
        if (candidate / "configs" / "example_org.yaml").exists():
            return candidate
    raise RuntimeError("run this from inside the Praetor repo")


REPO = find_repo_root()


class ScriptedProvider:
    """Deterministic stand-in for the judgment provider."""

    def __init__(self, judgment: ModelJudgment) -> None:
        self.judgment = judgment

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        return self.judgment

    def probe(self, canary_payload: Any) -> ProviderProbeResult:
        return ProviderProbeResult(
            success=True,
            provider_name="demo",
            model_name="demo-model",
        )


class SucceedingStamp:
    """Deterministic stand-in for the ticket stamp backend."""

    def stamp(self, stamp_id: str, payload: dict) -> StampBackendResult:
        return StampBackendResult(
            outcome=StampBackendOutcome.SUCCEEDED,
            payload={"ticket_id": "INC-DEMO-001"},
        )


def host_evidence(
    host_id: str,
    evidence_id: str,
    process: str,
    parent: str,
    *,
    dual_provenance: bool = True,
    primary_ambiguous: bool = False,
) -> EvidenceBundle:
    timestamp = datetime.now(UTC)
    facts = [
        EvidenceFact(
            evidence_id=evidence_id,
            normalized_fields={
                "host_id": host_id,
                "process_name": process,
                "parent_process_name": parent,
            },
            source_event_reference=f"sysmon:{host_id}:1",
            raw_source='{"_comment": "local-only"}',
            provenance_path="sysmon_event_log",
            ambiguity_flag=primary_ambiguous,
            timestamp=timestamp,
        )
    ]
    if dual_provenance:
        facts.append(
            EvidenceFact(
                evidence_id=f"{evidence_id}-sec",
                normalized_fields={"host_id": host_id, "event_id": 4624},
                source_event_reference=f"security:{host_id}:1",
                raw_source='{"_comment": "corroborating security event"}',
                provenance_path="windows_security_log",
                ambiguity_flag=False,
                timestamp=timestamp,
            )
        )
    return EvidenceBundle(facts=facts)


def model_proposes(
    disposition: Disposition,
    evidence_id: str,
    narrative: str,
    tells: list[str],
    *,
    corroborated: bool = False,
) -> ModelJudgment:
    refs = [CitedEvidenceRef(evidence_id=evidence_id, field_path="host_id")]
    if corroborated:
        refs.append(
            CitedEvidenceRef(evidence_id=f"{evidence_id}-sec", field_path="host_id")
        )
    return ModelJudgment(
        proposed_disposition=disposition,
        cited_evidence_refs=refs,
        key_tells=tells,
        org_config_refs=["containment_policy.default_action"],
        benign_alternatives=["scheduled IT automation"],
        benign_alternatives_ruled_out=["no change ticket; off-hours; encoded payload"],
        convergence_reasoning=(
            "office app spawning encoded PowerShell matches the intrusion pattern"
        ),
        narrative=narrative,
        model_name="demo-model",
        provider_name="demo",
    )


def set_host_allow_rules(store: Any, *host_ids: str) -> None:
    """Bind scoped host allow rules beneath ``default_action: escalate``."""
    base = fetch_active_snapshot(store.conn)
    assert base is not None
    policy = ContainmentPolicy(
        default_action="escalate",
        rules=[
            ContainmentRule(
                name=f"walkthrough_allow_{host_id}",
                action="allow",
                scope={"target_type": "host", "target_id": host_id},
            )
            for host_id in host_ids
        ],
    )
    payload = base.model_dump(mode="json")
    payload["containment_policy"] = policy.model_dump(mode="json")
    payload.pop("snapshot_hash", None)
    updated = base.model_copy(
        update={
            "containment_policy": policy,
            "snapshot_hash": compute_snapshot_hash_from_binding(payload),
        }
    )
    persist_org_config_snapshot(store.conn, updated, verbatim_render_text="walkthrough")
    store.conn.execute(
        "UPDATE active_org_config "
        "SET snapshot_hash = ?, verbatim_render_id = ? WHERE id = 1",
        (updated.snapshot_hash, "walkthrough-render"),
    )
    store.conn.commit()


_scenario_store: Any | None = None
_scenario_tmp: tempfile.TemporaryDirectory | None = None


def close_scenario_store() -> None:
    """Release the active scenario store and its temporary directory."""
    global _scenario_store, _scenario_tmp
    if _scenario_store is not None:
        _scenario_store.close()
        _scenario_store = None
    if _scenario_tmp is not None:
        _scenario_tmp.cleanup()
        _scenario_tmp = None


def fresh_store() -> Any:
    """Discard prior demo state and activate a clean org configuration."""
    global _scenario_store, _scenario_tmp
    close_scenario_store()
    _scenario_tmp = tempfile.TemporaryDirectory(prefix="praetor-walkthrough-")
    _scenario_store = open_state_store(Path(_scenario_tmp.name) / "walkthrough.db")
    init_annotation_schema(_scenario_store.conn)
    init_policy_gate_evaluation_schema(_scenario_store.conn)
    _scenario_store.conn.commit()
    activate_org_config(
        _scenario_store,
        REPO / "configs" / "example_org.yaml",
        token=SOC_TOKEN,
        verifier=VERIFIER,
    )
    return _scenario_store


def run_case(
    store: Any,
    *,
    alert_id: str,
    bundle: EvidenceBundle,
    judgment: ModelJudgment,
    label: str = "",
) -> Any:
    result = process_alert_intake(
        store,
        judgment_provider=ScriptedProvider(judgment),
        stamp_backend=SucceedingStamp(),
        alert_identity=alert_id,
        evidence_bundle=bundle,
    )
    edict = result.edict
    host = bundle.facts[0].normalized_fields["host_id"]
    directives = [
        directive
        for directive in fetch_outstanding_unrevoked_directives(store.conn)
        if directive.target_id == host
    ]
    print(f"alert             : {alert_id}")
    if label:
        print(f"scenario beat     : {label}")
    print(f"model proposed    : {judgment.proposed_disposition.value}")
    print(f"PRAETOR DECIDED   : {edict.final_disposition.value.upper()}")
    print(f"fault_flags       : {edict.fault_flags or '[]'}")
    print(f"system_fault_esc. : {edict.system_fault_escalation}")
    print(f"stamp_status      : {edict.stamp_status}")
    print(f"decision_id       : {edict.decision_id}")
    if directives:
        directive = directives[0]
        lifetime = (directive.expires_at - directive.issued_at).total_seconds()
        print("  >> CONTAINMENT DIRECTIVE EMITTED")
        print(
            f"     target          : {directive.target_type.value}:"
            f"{directive.target_id} scope={directive.scope}"
        )
        print(f"     lifetime        : {lifetime:.0f}s  (hard cap 300)")
        print(f"     status          : {directive.status.value}")
        print(f"     idempotency_key : {directive.idempotency_key}")
        print(f"     live_nc_hash    : {directive.live_never_contain_hash}")
    else:
        print("  >> no containment directive - nothing isolated")
    return result


def scenario_earned_auto_contain(store: Any) -> None:
    host = "WORKSTATION1"
    set_host_allow_rules(store, host)
    result = run_case(
        store,
        alert_id="ALERT-MAL-001",
        bundle=host_evidence(host, "ev-mal-1", "powershell.exe", "winword.exe"),
        judgment=model_proposes(
            Disposition.AUTO_CONTAIN,
            "ev-mal-1",
            "winword.exe spawned encoded PowerShell on WORKSTATION1.",
            ["encoded powershell", "office parent", "off-hours"],
            corroborated=True,
        ),
        label="earned auto_contain",
    )
    assert result.edict.final_disposition == Disposition.AUTO_CONTAIN


def scenario_benign_review(store: Any) -> None:
    result = run_case(
        store,
        alert_id="ALERT-BEN-001",
        bundle=host_evidence(
            "WORKSTATION7", "ev-ben-1", "explorer.exe", "userinit.exe"
        ),
        judgment=model_proposes(
            Disposition.STANDARD_REVIEW,
            "ev-ben-1",
            "Routine interactive logon shell on WORKSTATION7.",
            ["interactive logon", "explorer.exe"],
            corroborated=True,
        ),
        label="safe human-review floor",
    )
    assert result.edict.final_disposition == Disposition.STANDARD_REVIEW


def scenario_never_contain(store: Any) -> None:
    host = "DC01"
    add_emergency_never_contain(
        store,
        token=SOC_TOKEN,
        verifier=VERIFIER,
        target_specification={"target_type": "host", "target_id": host},
        lifetime_seconds=3600,
        audit_reason="domain controller - never auto-contain",
    )
    set_host_allow_rules(store, host)
    result = run_case(
        store,
        alert_id="ALERT-DC-001",
        bundle=host_evidence(host, "ev-dc-1", "powershell.exe", "services.exe"),
        judgment=model_proposes(
            Disposition.AUTO_CONTAIN,
            "ev-dc-1",
            "Suspicious PowerShell on domain controller DC01.",
            ["lsass handle access", "encoded command"],
            corroborated=True,
        ),
        label="live never-contain wins over allow",
    )
    assert result.edict.final_disposition == Disposition.ESCALATE
    assert "never_contain_live_conflict" in result.edict.fault_flags


def scenario_insufficient_corroboration(store: Any) -> None:
    host = "WORKSTATION2"
    set_host_allow_rules(store, host)
    result = run_case(
        store,
        alert_id="ALERT-THIN-001",
        bundle=host_evidence(
            host,
            "ev-thin-1",
            "powershell.exe",
            "winword.exe",
            dual_provenance=True,
            primary_ambiguous=True,
        ),
        judgment=model_proposes(
            Disposition.AUTO_CONTAIN,
            "ev-thin-1",
            "Only the ambiguous Sysmon fact is cited; the second fact is unused.",
            ["encoded powershell"],
            corroborated=False,
        ),
        label="corroboration floor",
    )
    assert "insufficient_corroboration" in result.edict.fault_flags


def scenario_not_allowlisted(store: Any) -> None:
    result = run_case(
        store,
        alert_id="ALERT-POSTURE-001",
        bundle=host_evidence(
            "WORKSTATION9", "ev-pos-1", "powershell.exe", "winword.exe"
        ),
        judgment=model_proposes(
            Disposition.AUTO_CONTAIN,
            "ev-pos-1",
            "Strong evidence, but the target has no scoped allow rule.",
            ["encoded powershell", "office parent"],
            corroborated=True,
        ),
        label="escalate-by-default posture",
    )
    assert result.edict.final_disposition == Disposition.ESCALATE
    print("pin: containment not granted by omission")


def scenario_rate_limit(store: Any) -> None:
    host = "WORKSTATION-RATE"
    set_host_allow_rules(store, host)
    snapshot = fetch_active_snapshot(store.conn)
    assert snapshot is not None
    key = rate_limit_scope_key("per_host", target_type="host", target_id=host)
    set_rate_counter(store.conn, key, snapshot.rate_limit_policy.ceilings.per_host)
    store.conn.commit()
    result = run_case(
        store,
        alert_id="ALERT-RATE-001",
        bundle=host_evidence(host, "ev-rate-1", "powershell.exe", "winword.exe"),
        judgment=model_proposes(
            Disposition.AUTO_CONTAIN,
            "ev-rate-1",
            "Authorized target arrives after its per-host ceiling is reached.",
            ["encoded powershell", "rate ceiling"],
            corroborated=True,
        ),
        label="transactional rate-limit refusal",
    )
    assert result.edict.final_disposition == Disposition.ESCALATE
    assert "rate_limit_exceeded" in result.edict.fault_flags


def scenario_circuit_breaker(store: Any) -> None:
    host = "WORKSTATION-BREAKER"
    set_host_allow_rules(store, host)
    set_breaker_open(store.conn, BreakerDomain.CONTAINMENT, open_=True)
    store.conn.execute(
        "UPDATE circuit_breaker_state SET window_started_at = ? WHERE domain = ?",
        (datetime.now(UTC).isoformat(), BreakerDomain.CONTAINMENT.value),
    )
    store.conn.commit()
    result = run_case(
        store,
        alert_id="ALERT-BREAKER-001",
        bundle=host_evidence(host, "ev-breaker-1", "powershell.exe", "winword.exe"),
        judgment=model_proposes(
            Disposition.AUTO_CONTAIN,
            "ev-breaker-1",
            "Authorized target evaluated while containment breaker is open.",
            ["encoded powershell", "breaker open"],
            corroborated=True,
        ),
        label="containment circuit breaker",
    )
    assert result.edict.final_disposition == Disposition.ESCALATE
    assert "containment_breaker_open" in result.edict.fault_flags


def scenario_progressive_report(store: Any) -> None:
    now = datetime.now(UTC)
    rows = [
        ("report-allow", Disposition.AUTO_CONTAIN, Disposition.AUTO_CONTAIN),
        ("report-thin", Disposition.AUTO_CONTAIN, Disposition.ESCALATE),
        ("report-review", Disposition.STANDARD_REVIEW, Disposition.STANDARD_REVIEW),
    ]
    with critical_transaction(store.conn):
        for index, (decision_id, proposed, final) in enumerate(rows):
            record_policy_gate_evaluation(
                store.conn,
                decision_id=decision_id,
                target_type="host",
                asset_class="workstation",
                proposed=proposed,
                final=final,
                evaluated_at=now - timedelta(minutes=index),
            )
    report = build_progressive_authorization_report(
        store.conn,
        window_start=now - timedelta(hours=1),
        window_end=now + timedelta(minutes=1),
    )
    print("PROGRESSIVE AUTHORIZATION REPORT (read-only)")
    print(f"  read_only={report.read_only}")
    for dimension in report.policy_gate_by_dimension:
        rate = dimension.policy_gate_override_rate
        rate_text = f"{rate:.0%}" if rate is not None else "n/a"
        print(
            f"  {dimension.target_type}/{dimension.asset_class}: "
            f"evals={dimension.policy_gate_evaluations_total} "
            f"overrides={dimension.policy_gate_override_total} "
            f"override_rate={rate_text}"
        )
    assert report.read_only is True


def scenario_similar_case_exemplars(store: Any) -> None:
    host = "WORKSTATION-EXEMPLAR"
    set_host_allow_rules(store, host)
    source = run_case(
        store,
        alert_id="ALERT-EXEMPLAR-SOURCE",
        bundle=host_evidence(host, "ev-exemplar-1", "powershell.exe", "winword.exe"),
        judgment=model_proposes(
            Disposition.AUTO_CONTAIN,
            "ev-exemplar-1",
            "Confirmed office-to-PowerShell precedent.",
            ["encoded powershell", "office parent"],
            corroborated=True,
        ),
        label="seed a human-confirmed precedent",
    )
    with critical_transaction(store.conn):
        submit_annotation(
            store.conn,
            token=ANALYST_TOKEN,
            verifier=VERIFIER,
            decision_id=source.edict.decision_id,
            disposition_correct=True,
            corrected_disposition=None,
            comment="confirmed macro-to-powershell intrusion pattern",
            timestamp=datetime.now(UTC),
        )
    facts = [
        {
            "evidence_id": "ev-query-1",
            "normalized_fields": {
                "host_id": "WORKSTATION3",
                "process_name": "powershell.exe",
                "parent_process_name": "winword.exe",
            },
            "provenance_path": "sysmon_event_log",
            "ambiguity_flag": False,
        }
    ]
    payload = build_judgment_prompt_payload_with_similar_cases(
        store.conn,
        evidence_facts=facts,
        evidence_bundle_hash="demo-bundle-hash",
        org_config_snapshot_hash="demo-snapshot-hash",
        org_config_verbatim="(statute omitted in demo)",
    )
    block = payload.get("prompt_exemplar_block")
    print("prompt has prompt_exemplar_block:", block is not None)
    exemplars = block.get("exemplars", []) if block else []
    print(f"exemplar count: {len(exemplars)}")
    for exemplar in exemplars:
        print(f"  - {exemplar.get('exemplar_id')}: {exemplar.get('disposition')}")
        print(f"    {(exemplar.get('summary') or '')[:100]}...")
    print(
        "exemplar_scope:",
        payload["instructions"].get("exemplar_scope", "")[:100],
        "...",
    )
    assert block is not None


def scenario_statute_curation(store: Any) -> None:
    host = "WORKSTATION-CURATION"
    set_host_allow_rules(store, host)
    source = run_case(
        store,
        alert_id="ALERT-CURATION-SOURCE",
        bundle=host_evidence(host, "ev-curation-1", "powershell.exe", "winword.exe"),
        judgment=model_proposes(
            Disposition.AUTO_CONTAIN,
            "ev-curation-1",
            "A reviewed decision becomes provenance for a proposed statute edit.",
            ["encoded powershell", "office parent"],
            corroborated=True,
        ),
        label="seed curation provenance",
    )
    with critical_transaction(store.conn):
        annotation = submit_annotation(
            store.conn,
            token=ANALYST_TOKEN,
            verifier=VERIFIER,
            decision_id=source.edict.decision_id,
            disposition_correct=True,
            corrected_disposition=None,
            comment="confirmed macro-to-powershell intrusion pattern",
            timestamp=datetime.now(UTC),
        )
    base = load_org_config_source(REPO / "configs" / "example_org.yaml").document
    patterns = copy.deepcopy(base["normal_admin_patterns"])
    patterns["patterns"] = list(patterns["patterns"]) + [
        {
            "name": "walkthrough_eng_jumphost",
            "description": "SOC-confirmed admin pattern from annotation review",
        }
    ]
    proposed = build_proposed_statute_artifact(
        base,
        edits=[
            StatuteEdit(
                section="normal_admin_patterns",
                content=patterns,
                rationale="Sustained annotation evidence for eng jumphost pattern",
                source_decision_ids=(source.edict.decision_id,),
            )
        ],
        source_annotations=[
            SourceAnnotationRef(
                decision_id=source.edict.decision_id,
                annotation_id=annotation.annotation_id,
                disposition_correct=True,
                comment="confirmed macro-to-powershell intrusion pattern",
                reviewer_identity="analyst-1",
                timestamp=annotation.annotation.timestamp,
            )
        ],
        workflow_id="walkthrough-wf-001",
        config_version="statute-proposed-walkthrough",
    )
    metadata = proposed["version_metadata"]
    print("artifact_kind     :", metadata["artifact_kind"])
    print("activation_status :", metadata["activation_status"])
    try:
        run_preflight(proposed, verbatim_text=render_proposed_statute_yaml(proposed))
        raise AssertionError("proposed statute unexpectedly passed preflight")
    except PreflightError as exc:
        print(f"preflight refused : {exc.code}")
    print("pin: proposed_for_review_only")


@dataclass(frozen=True)
class Scenario:
    """One selectable demo path plus the explanation shown alongside it."""

    key: str
    label: str
    headline: str
    architecture: str
    wiring: str
    gotcha: str
    run: Callable[[Any], None]
    hint: str | None = None


SCENARIO_LIST: tuple[Scenario, ...] = (
    Scenario(
        key="earned_auto_contain",
        label="Containment approved",
        headline="Strong evidence + an allowlisted host → isolate it for five minutes.",
        architecture=(
            "The model says contain. Praetor checks policy and evidence, then "
            "issues a short-lived containment order for that host."
        ),
        wiring=(
            "WORKSTATION1 is on the allowlist. Two independent log sources back "
            "the same host. The order expires after 300 seconds."
        ),
        gotcha=(
            "Praetor writes the order; your EDR still has to carry it out. A "
            "confident model is never enough on its own."
        ),
        run=scenario_earned_auto_contain,
    ),
    Scenario(
        key="benign_review",
        label="Looks benign — send to review",
        headline="Nothing scary here, so a human still gets the ticket and nothing is isolated.",
        architecture=(
            "When the model says this looks routine, Praetor keeps it in the "
            "human review queue and does not authorize containment."
        ),
        wiring=(
            "A normal interactive logon shell on WORKSTATION7. No allowlist "
            "trickery — the safe path is review by default."
        ),
        gotcha=(
            "Review is not auto-close. Praetor never quietly dismisses an alert; "
            "uncertainty always goes to a person."
        ),
        run=scenario_benign_review,
    ),
    Scenario(
        key="never_contain",
        label="Never-contain (domain controller)",
        headline="Even with an allow rule, a domain controller on the never-contain list cannot be auto-isolated.",
        architecture=(
            "Never-contain is a hard stop. Praetor checks it before issuing any "
            "containment order."
        ),
        wiring=(
            "DC01 is allowlisted and the model wants containment — but an "
            "emergency never-contain entry for that host is already live."
        ),
        gotcha=(
            "Never-contain beats allow. The alert escalates with an explicit "
            "reason; it is not silently dropped."
        ),
        run=scenario_never_contain,
    ),
    Scenario(
        key="insufficient_corroboration",
        label="Thin evidence",
        headline="One shaky log line is not enough to isolate a host.",
        architecture=(
            "Praetor only counts evidence the model actually points to — not "
            "every log sitting nearby in the alert."
        ),
        wiring=(
            "A second log source exists in the bundle, but the model only cites "
            "one ambiguous Sysmon event."
        ),
        gotcha=(
            "Extra telemetry in the pile does nothing unless the model cites it. "
            "That stops unrelated noise from unlocking containment."
        ),
        run=scenario_insufficient_corroboration,
    ),
    Scenario(
        key="not_allowlisted",
        label="Not on the allowlist",
        headline="Great evidence still loses if this host was never authorized for auto-contain.",
        architecture=(
            "By default Praetor escalates. Containment only happens when a host "
            "(or class of hosts) is explicitly allowed."
        ),
        wiring=(
            "Evidence for WORKSTATION9 is solid, but no allow rule covers that "
            "host."
        ),
        gotcha=(
            "Good evidence and policy permission are separate checks. Missing "
            "from the allowlist means no auto-contain — full stop."
        ),
        run=scenario_not_allowlisted,
    ),
    Scenario(
        key="rate_limit",
        label="Rate limit hit",
        headline="This host already hit its containment ceiling, so Praetor refuses another isolation.",
        architecture=(
            "Praetor caps how many hosts (and how often) you can auto-contain, "
            "so one noisy incident cannot take half the floor offline."
        ),
        wiring=(
            "The host is allowlisted and the evidence is fine — we just already "
            "used up its per-host containment budget."
        ),
        gotcha=(
            "This is a deliberate safety limit, not a crash. The alert escalates "
            "so a human can decide what to do next."
        ),
        run=scenario_rate_limit,
    ),
    Scenario(
        key="circuit_breaker",
        label="Circuit breaker tripped",
        headline="Containment is paused org-wide until the breaker cools down.",
        architecture=(
            "If auto-contain keeps failing or thrashing, Praetor opens a breaker "
            "and blocks new isolation until the window expires."
        ),
        wiring=(
            "The host would otherwise qualify, but the containment breaker is "
            "already open."
        ),
        gotcha=(
            "While the breaker is open, nothing new gets isolated. It recovers "
            "when the cooldown window ends — not by hoping the next contain "
            "succeeds."
        ),
        run=scenario_circuit_breaker,
    ),
    Scenario(
        key="progressive_report",
        label="Override scoreboard",
        headline="A read-only report: how often did policy overturn the model?",
        architecture=(
            "This is a scoreboard, not a containment decision. It counts past "
            "cases where the model wanted one thing and policy chose another."
        ),
        wiring=(
            "We plant three past decisions for workstations; in one of them "
            "policy overrode the model (33%)."
        ),
        gotcha=(
            "Seeing a high override rate does not widen who can be auto-contained. "
            "Changing real authority is still a separate human approval."
        ),
        run=scenario_progressive_report,
    ),
    Scenario(
        key="similar_case_exemplars",
        label="Similar past cases",
        headline="Show the model a few human-confirmed precedents — without giving them power.",
        architecture=(
            "When a new alert looks like an old confirmed case, Praetor can "
            "include a short example in the prompt so the model has context."
        ),
        wiring=(
            "We save a real decision, an analyst marks it correct, then a "
            "similar office→PowerShell alert asks for precedents."
        ),
        gotcha=(
            "Examples only help the model think. Policy still decides whether "
            "anything gets contained."
        ),
        run=scenario_similar_case_exemplars,
    ),
    Scenario(
        key="statute_curation",
        label="Propose a policy edit",
        headline="Analysts can draft a policy change from review notes — but it cannot go live by itself.",
        architecture=(
            "Praetor does not invent the edit. Humans draft the org-policy "
            "change from confirmed decisions and analyst notes; Praetor "
            "packages that draft as a review-only artifact."
        ),
        wiring=(
            "A finalized decision plus an analyst note support a draft change to "
            "normal admin patterns."
        ),
        gotcha=(
            "The draft is refused for activation on purpose. A SOC lead must "
            "promote it in a separate workflow before it becomes real policy."
        ),
        run=scenario_statute_curation,
        hint=(
            "Related path: the org-config sweep can empirically propose "
            "principals, assets, and admin patterns from telemetry. It still "
            "never infers statute, containment policy, or never-contain — and "
            "those artifacts are also refused until a SOC lead promotes them."
        ),
    ),
)

SCENARIOS: dict[str, Scenario] = {s.key: s for s in SCENARIO_LIST}


def explainer_markdown(scenario: Scenario) -> str:
    hint = f"\n\n**Hint.** {scenario.hint}" if scenario.hint else ""
    return (
        f"### {scenario.label}\n\n"
        f"{scenario.headline}\n\n"
        f"**What happens.** {scenario.architecture}\n\n"
        f"**Setup.** {scenario.wiring}\n\n"
        f"**Why it matters.** {scenario.gotcha}"
        f"{hint}\n\n"
        "---"
    )


def run_scenario(key: str, *, show: Callable[[str], None] | None = None) -> None:
    """Boot a clean store, explain the selected path, and execute it."""
    scenario = SCENARIOS[key]
    store = fresh_store()
    render = show if show is not None else print
    render(explainer_markdown(scenario))
    print(f"SCENARIO START: {key}")
    scenario.run(store)
    print(f"SCENARIO COMPLETE: {key}")


def capture_scenario(key: str) -> str:
    """Run one scenario headlessly and return only its printed engine output."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        run_scenario(key, show=lambda _text: None)
    return buffer.getvalue()


@contextlib.contextmanager
def scenario_session() -> Iterator[None]:
    """Guarantee the scenario store is released when a sweep ends."""
    try:
        yield
    finally:
        close_scenario_store()
