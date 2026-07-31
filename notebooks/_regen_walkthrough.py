"""Regenerate the interactive Praetor walkthrough with executed CI outputs."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "praetor_walkthrough.ipynb"


def md(source: str) -> object:
    return new_markdown_cell(source.strip() + "\n")


def code(source: str, *, metadata: dict | None = None) -> object:
    return new_code_cell(source.strip() + "\n", metadata=metadata or {})


def build() -> nbformat.NotebookNode:
    cells = [
        md(
            """
# Praetor interactive walkthrough

**Post-detection disposition engine.** An alert already fired; Praetor decides what happens next.

> The model recommends. The system authorizes.

Choose one scenario below. Changing the radio selection immediately destroys the
previous throwaway SQLite store, activates a clean org configuration, wires the
selected precondition, and runs only that scenario.

The model provider and ticket stamp are deterministic stand-ins. **Everything
downstream is the real Praetor engine and library surface.**

| Disposition | Meaning |
|---|---|
| `standard_review` | safe floor — a human still sees it |
| `escalate` | prioritized human review |
| `auto_contain` | bounded directive before human review |

**No `auto_close`.** Uncertainty always routes to a human.

The final all-scenario verification cell is hidden in notebook UIs. It executes
every scenario during regeneration so CI can verify paths that are not
simultaneously visible in the live picker.
"""
        ),
        md(
            """
## Setup

Install the optional walkthrough dependency with:

```bash
python -m pip install -e ".[walkthrough]"
```
"""
        ),
        code(
            """
import copy
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import ipywidgets as widgets
from IPython.display import Markdown, clear_output, display

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
from praetor.judgment.provider import JudgmentRequest, ProviderProbeResult
from praetor.judgment.prompt import build_judgment_prompt_payload_with_similar_cases
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


def find_repo_root() -> Path:
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "configs" / "example_org.yaml").exists():
            return candidate
    raise RuntimeError("run this notebook from inside the Praetor repo")


REPO = find_repo_root()
print("Praetor repo:", REPO)
"""
        ),
        md(
            """
## Shared demo wiring

The helpers below provide the two deliberate stand-ins, construct evidence and
judgments, activate clean state, and print the decision boundary consistently.
Scenario functions only add the precondition they are meant to teach.
"""
        ),
        code(
            """
class ScriptedProvider:
    def __init__(self, judgment: ModelJudgment) -> None:
        self.judgment = judgment

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        return self.judgment

    def probe(self, canary_payload):
        return ProviderProbeResult(
            success=True,
            provider_name="demo",
            model_name="demo-model",
        )


class SucceedingStamp:
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
    disposition,
    evidence_id,
    narrative,
    tells,
    *,
    corroborated: bool = False,
):
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
        benign_alternatives_ruled_out=[
            "no change ticket; off-hours; encoded payload"
        ],
        convergence_reasoning=(
            "office app spawning encoded PowerShell matches the intrusion pattern"
        ),
        narrative=narrative,
        model_name="demo-model",
        provider_name="demo",
    )


def set_host_allow_rules(store, *host_ids: str) -> None:
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
    persist_org_config_snapshot(
        store.conn,
        updated,
        verbatim_render_text="walkthrough",
    )
    store.conn.execute(
        "UPDATE active_org_config "
        "SET snapshot_hash = ?, verbatim_render_id = ? WHERE id = 1",
        (updated.snapshot_hash, "walkthrough-render"),
    )
    store.conn.commit()


SOC_TOKEN = "soc-lead-token"
ANALYST_TOKEN = "analyst-token"
VERIFIER = PrincipalMapVerifier(
    {
        SOC_TOKEN: Principal(identity="soc-lead-1", role="soc_lead"),
        ANALYST_TOKEN: Principal(identity="analyst-1", role="analyst"),
    }
)

_scenario_store = None
_scenario_tmp = None


def close_scenario_store() -> None:
    global _scenario_store, _scenario_tmp
    if _scenario_store is not None:
        _scenario_store.close()
        _scenario_store = None
    if _scenario_tmp is not None:
        _scenario_tmp.cleanup()
        _scenario_tmp = None


def fresh_store():
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


def run_case(store, *, alert_id, bundle, judgment, label: str = ""):
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
        lifetime_seconds = (
            directive.expires_at - directive.issued_at
        ).total_seconds()
        print("  >> CONTAINMENT DIRECTIVE EMITTED")
        print(
            f"     target          : {directive.target_type.value}:"
            f"{directive.target_id} scope={directive.scope}"
        )
        print(f"     lifetime        : {lifetime_seconds:.0f}s  (hard cap 300)")
        print(f"     status          : {directive.status.value}")
        print(f"     idempotency_key : {directive.idempotency_key}")
        print(f"     live_nc_hash    : {directive.live_never_contain_hash}")
    else:
        print("  >> no containment directive — nothing isolated")
    return result
"""
        ),
        md(
            """
## Scenario implementations

Each function receives a newly activated store. The registry later binds these
functions to the radio labels and their selected-only explanation.
"""
        ),
        code(
            """
def scenario_earned_auto_contain(store):
    host = "WORKSTATION1"
    set_host_allow_rules(store, host)
    result = run_case(
        store,
        alert_id="ALERT-MAL-001",
        bundle=host_evidence(
            host, "ev-mal-1", "powershell.exe", "winword.exe"
        ),
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


def scenario_benign_review(store):
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


def scenario_never_contain(store):
    host = "DC01"
    add_emergency_never_contain(
        store,
        token=SOC_TOKEN,
        verifier=VERIFIER,
        target_specification={"target_type": "host", "target_id": host},
        lifetime_seconds=3600,
        audit_reason="domain controller — never auto-contain",
    )
    set_host_allow_rules(store, host)
    result = run_case(
        store,
        alert_id="ALERT-DC-001",
        bundle=host_evidence(
            host, "ev-dc-1", "powershell.exe", "services.exe"
        ),
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


def scenario_insufficient_corroboration(store):
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


def scenario_not_allowlisted(store):
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


def scenario_rate_limit(store):
    host = "WORKSTATION-RATE"
    set_host_allow_rules(store, host)
    snapshot = fetch_active_snapshot(store.conn)
    assert snapshot is not None
    key = rate_limit_scope_key("per_host", target_type="host", target_id=host)
    set_rate_counter(
        store.conn,
        key,
        snapshot.rate_limit_policy.ceilings.per_host,
    )
    store.conn.commit()
    result = run_case(
        store,
        alert_id="ALERT-RATE-001",
        bundle=host_evidence(
            host, "ev-rate-1", "powershell.exe", "winword.exe"
        ),
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


def scenario_circuit_breaker(store):
    host = "WORKSTATION-BREAKER"
    set_host_allow_rules(store, host)
    set_breaker_open(
        store.conn,
        BreakerDomain.CONTAINMENT,
        open_=True,
    )
    store.conn.execute(
        "UPDATE circuit_breaker_state "
        "SET window_started_at = ? WHERE domain = ?",
        (datetime.now(UTC).isoformat(), BreakerDomain.CONTAINMENT.value),
    )
    store.conn.commit()
    result = run_case(
        store,
        alert_id="ALERT-BREAKER-001",
        bundle=host_evidence(
            host, "ev-breaker-1", "powershell.exe", "winword.exe"
        ),
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


def scenario_progressive_report(store):
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


def scenario_similar_case_exemplars(store):
    host = "WORKSTATION-EXEMPLAR"
    set_host_allow_rules(store, host)
    source = run_case(
        store,
        alert_id="ALERT-EXEMPLAR-SOURCE",
        bundle=host_evidence(
            host, "ev-exemplar-1", "powershell.exe", "winword.exe"
        ),
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
        print(
            f"  - {exemplar.get('exemplar_id')}: "
            f"{exemplar.get('disposition')}"
        )
        print(f"    {(exemplar.get('summary') or '')[:100]}...")
    print(
        "exemplar_scope:",
        payload["instructions"].get("exemplar_scope", "")[:100],
        "...",
    )
    assert block is not None


def scenario_statute_curation(store):
    host = "WORKSTATION-CURATION"
    set_host_allow_rules(store, host)
    source = run_case(
        store,
        alert_id="ALERT-CURATION-SOURCE",
        bundle=host_evidence(
            host, "ev-curation-1", "powershell.exe", "winword.exe"
        ),
        judgment=model_proposes(
            Disposition.AUTO_CONTAIN,
            "ev-curation-1",
            "A reviewed decision becomes provenance for a proposed statute edit.",
            ["encoded powershell", "office parent"],
            corroborated=True,
        ),
        label="seed curation provenance",
    )
    base = load_org_config_source(
        REPO / "configs" / "example_org.yaml"
    ).document
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
                annotation_id=1,
                disposition_correct=True,
                comment="confirmed macro-to-powershell intrusion pattern",
                reviewer_identity="analyst-1",
                timestamp=datetime.now(UTC),
            )
        ],
        workflow_id="walkthrough-wf-001",
        config_version="statute-proposed-walkthrough",
    )
    metadata = proposed["version_metadata"]
    print("artifact_kind     :", metadata["artifact_kind"])
    print("activation_status :", metadata["activation_status"])
    try:
        run_preflight(
            proposed,
            verbatim_text=render_proposed_statute_yaml(proposed),
        )
        raise AssertionError("proposed statute unexpectedly passed preflight")
    except PreflightError as exc:
        print(f"preflight refused : {exc.code}")
    print("pin: proposed_for_review_only")
"""
        ),
        md(
            """
## Scenario registry

The explanation is data beside the scenario, rather than prose spread across
the notebook. That keeps architecture, setup wiring, and the safety caveat
visible only for the selected path.
"""
        ),
        code(
            """
SCENARIOS = {
    "earned_auto_contain": {
        "label": "Earned auto-contain",
        "architecture": (
            "The provider proposes AUTO_CONTAIN, then PolicyGate independently "
            "authorizes the cited host and the engine commits the directive with "
            "the edict after the terminal ticket stamp."
        ),
        "wiring": (
            "A scoped host allow rule is activated and both Sysmon and Windows "
            "Security facts are cited. The emitted directive is bounded to the "
            "configured 300-second lifetime."
        ),
        "gotcha": (
            "Praetor emits an auditable directive; this demo does not actuate an "
            "EDR. A strong model judgment alone is never authority."
        ),
        "run": scenario_earned_auto_contain,
    },
    "benign_review": {
        "label": "Benign standard review",
        "architecture": (
            "STANDARD_REVIEW is the safe human-review floor. PolicyGate does not "
            "need to manufacture a containment authorization for a non-containment "
            "proposal."
        ),
        "wiring": (
            "The scripted judgment classifies a routine interactive shell and the "
            "normal intake path persists the resulting edict."
        ),
        "gotcha": (
            "Standard review is not auto-close. The event remains visible to a "
            "human and no containment directive is emitted."
        ),
        "run": scenario_benign_review,
    },
    "never_contain": {
        "label": "Live never-contain conflict",
        "architecture": (
            "Emergency never-contain is live authorization state checked by the "
            "gate and rechecked at directive persistence boundaries."
        ),
        "wiring": (
            "DC01 receives both an explicit allow and an authenticated emergency "
            "never-contain entry before the same AUTO_CONTAIN proposal is processed."
        ),
        "gotcha": (
            "Never-contain wins over allow. The final result is ESCALATE with "
            "never_contain_live_conflict, not a silent suppression."
        ),
        "run": scenario_never_contain,
    },
    "insufficient_corroboration": {
        "label": "Insufficient corroboration",
        "architecture": (
            "Host authorization evaluates only cited evidence, not every fact in "
            "the correlated bundle."
        ),
        "wiring": (
            "The bundle contains a second provenance source, but the judgment cites "
            "only one ambiguous Sysmon host fact. That sole citation cannot earn "
            "containment under the current temporary floor."
        ),
        "gotcha": (
            "Adding evidence to a bundle does nothing unless the judgment cites the "
            "relevant fact. Citation anchoring prevents unrelated telemetry from "
            "silently granting authority."
        ),
        "run": scenario_insufficient_corroboration,
    },
    "not_allowlisted": {
        "label": "Target not allowlisted",
        "architecture": (
            "ContainmentPolicy uses default_action=escalate. Scoped rules are the "
            "positive authorization surface; omission is not permission."
        ),
        "wiring": (
            "The evidence is fully corroborated, but no rule allows WORKSTATION9."
        ),
        "gotcha": (
            "Evidence quality and policy authority are independent gates. Perfect "
            "evidence cannot bypass an absent allow rule."
        ),
        "run": scenario_not_allowlisted,
    },
    "rate_limit": {
        "label": "Rate limit exceeded",
        "architecture": (
            "The policy layer evaluates sliding-window counters for every applicable "
            "configured scope before directive persistence."
        ),
        "wiring": (
            "The target is explicitly allowed, then its per-host counter is seeded "
            "at the configured ceiling before intake."
        ),
        "gotcha": (
            "A rate-limit refusal is an authorization/safety escalation, not an "
            "infrastructure fault. It also contributes to breaker failure tracking."
        ),
        "run": scenario_rate_limit,
    },
    "circuit_breaker": {
        "label": "Containment circuit breaker open",
        "architecture": (
            "The containment breaker is independent of provider health and blocks "
            "new AUTO_CONTAIN authorization while its current window remains open."
        ),
        "wiring": (
            "The target is allowed and corroborated, but the containment breaker row "
            "is opened with a fresh window timestamp."
        ),
        "gotcha": (
            "The breaker recovers by window elapse because blocking containment also "
            "blocks the success signals that could otherwise close it."
        ),
        "run": scenario_circuit_breaker,
    },
    "progressive_report": {
        "label": "Progressive authorization report",
        "architecture": (
            "The report is a read-only aggregation over persisted PolicyGate "
            "evaluation and annotation records; it never promotes policy itself."
        ),
        "wiring": (
            "Three evaluation rows are seeded with one model-to-gate override, then "
            "grouped by target type and asset class."
        ),
        "gotcha": (
            "Override rates are decision support, not an automatic allowlist tuner. "
            "Human policy promotion remains a separate authenticated workflow."
        ),
        "run": scenario_progressive_report,
    },
    "similar_case_exemplars": {
        "label": "Human-confirmed exemplars",
        "architecture": (
            "Similar-case retrieval reads finalized edicts plus post-hoc analyst "
            "annotations and injects bounded illustration-only exemplars into the "
            "judgment prompt."
        ),
        "wiring": (
            "A real decision is persisted, an analyst marks it correct, and a "
            "matching office-to-PowerShell query asks the prompt builder for precedents."
        ),
        "gotcha": (
            "Exemplars influence model context but carry no containment authority. "
            "The deterministic PolicyGate still decides the final action."
        ),
        "run": scenario_similar_case_exemplars,
    },
    "statute_curation": {
        "label": "Review-only statute curation",
        "architecture": (
            "Curation produces a provenance-linked proposed statute artifact outside "
            "the active configuration path."
        ),
        "wiring": (
            "A finalized decision ID and annotation reference support a proposed "
            "normal-admin-pattern edit."
        ),
        "gotcha": (
            "The proposal is deliberately non-activatable. Preflight refuses it until "
            "a SOC lead performs the separate promotion workflow."
        ),
        "run": scenario_statute_curation,
    },
}


def run_scenario(name: str) -> None:
    scenario = SCENARIOS[name]
    store = fresh_store()
    display(
        Markdown(
            f"### {scenario['label']}\\n\\n"
            f"**Architecture.** {scenario['architecture']}\\n\\n"
            f"**Wiring.** {scenario['wiring']}\\n\\n"
            f"**Gotcha.** {scenario['gotcha']}\\n\\n"
            "---"
        )
    )
    print(f"SCENARIO START: {name}")
    scenario["run"](store)
    print(f"SCENARIO COMPLETE: {name}")
"""
        ),
        md(
            """
## Pick a scenario

Selecting a different radio option immediately force-refreshes the explanation,
database, configuration, and result for that scenario.
"""
        ),
        code(
            """
scenario_options = [
    (scenario["label"], name)
    for name, scenario in SCENARIOS.items()
]
scenario_picker = widgets.RadioButtons(
    options=scenario_options,
    value=next(iter(SCENARIOS)),
    description="Scenario:",
    layout=widgets.Layout(width="max-content"),
    style={"description_width": "initial"},
)
scenario_output = widgets.Output()


def refresh_selected_scenario(change) -> None:
    if change.get("name") != "value" or change.get("new") is None:
        return
    with scenario_output:
        clear_output(wait=True)
        run_scenario(change["new"])


scenario_picker.observe(refresh_selected_scenario, names="value")
display(widgets.VBox([scenario_picker, scenario_output]))
with scenario_output:
    run_scenario(scenario_picker.value)
print("INTERACTIVE PICKER READY")
"""
        ),
        code(
            """
print("CI SCENARIO SWEEP START")
try:
    for scenario_name in SCENARIOS:
        run_scenario(scenario_name)
    print("CI SCENARIO SWEEP COMPLETE")
finally:
    close_scenario_store()
""",
            metadata={
                "jupyter": {
                    "source_hidden": True,
                    "outputs_hidden": True,
                },
                "tags": ["ci-verification"],
            },
        ),
        code(
            """
close_scenario_store()
print("walkthrough scenario store closed")
"""
        ),
    ]

    notebook = new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
    )
    notebook.nbformat = 4
    notebook.nbformat_minor = 5
    return notebook


def main() -> None:
    notebook = build()
    client = NotebookClient(notebook, timeout=240, kernel_name="python3")
    client.execute()
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.metadata.pop("execution", None)
    nbformat.write(notebook, OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
