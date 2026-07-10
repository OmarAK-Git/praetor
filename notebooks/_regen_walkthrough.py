"""Regenerate notebooks/praetor_walkthrough.ipynb (valid nbformat + executed outputs)."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "praetor_walkthrough.ipynb"


def md(source: str) -> object:
    return new_markdown_cell(source.strip() + "\n")


def code(source: str) -> object:
    return new_code_cell(source.strip() + "\n")


def build() -> nbformat.NotebookNode:
    cells = [
        md(
            """
# Praetor walkthrough

**Post-detection disposition engine.** An alert already fired; Praetor decides what happens next.

> The model recommends. The system authorizes.

Offline + deterministic: LLM and ticket stamp are scripted. **Everything downstream is the real engine.**

| Disposition | Meaning |
|---|---|
| `standard_review` | safe floor — human still sees it |
| `escalate` | prioritized human review |
| `auto_contain` | bounded directive *before* human review |

**No `auto_close`.** Uncertainty always routes to a human.

### Tour map

| Act | What you see |
|---|---|
| **I — Thesis** | contain · review · refuse on a DC |
| **II — V2** | corroboration · escalate-default · progressive report · exemplars · statute curation |
"""
        ),
        md("## Setup"),
        md("### Imports"),
        code(
            """
import copy
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

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
from praetor.reporting.progressive_authorization import (
    build_progressive_authorization_report,
)
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import open_state_store
from praetor.tickets.stamp import StampBackendOutcome, StampBackendResult


def find_repo_root() -> Path:
    here = Path.cwd().resolve()
    for cand in (here, *here.parents):
        if (cand / "configs" / "example_org.yaml").exists():
            return cand
    raise RuntimeError("run this notebook from inside the Praetor repo")


REPO = find_repo_root()
print("Praetor repo:", REPO)
"""
        ),
        md(
            """
### Helpers

Scripted LLM + succeeding stamp. Downstream of those two stand-ins is the real engine.
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
            success=True, provider_name="demo", model_name="demo-model"
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
) -> EvidenceBundle:
    # Sysmon (+ optional security) facts for host targeting / corroboration.
    ts = datetime.now(UTC)
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
            ambiguity_flag=False,
            timestamp=ts,
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
                timestamp=ts,
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
        benign_alternatives_ruled_out=["no change ticket; off-hours; encoded payload"],
        convergence_reasoning=(
            "office app spawning encoded PowerShell matches the intrusion pattern"
        ),
        narrative=narrative,
        model_name="demo-model",
        provider_name="demo",
    )


CASE_LOG: list[dict] = []


def run_case(store, *, alert_id, bundle, judgment, label: str = ""):
    result = process_alert_intake(
        store,
        judgment_provider=ScriptedProvider(judgment),
        stamp_backend=SucceedingStamp(),
        alert_identity=alert_id,
        evidence_bundle=bundle,
    )
    e = result.edict
    host = bundle.facts[0].normalized_fields["host_id"]
    dirs = [
        d
        for d in fetch_outstanding_unrevoked_directives(store.conn)
        if d.target_id == host
    ]
    print(f"alert             : {alert_id}")
    if label:
        print(f"beat              : {label}")
    print(f"model proposed    : {judgment.proposed_disposition.value}")
    print(f"PRAETOR DECIDED   : {e.final_disposition.value.upper()}")
    print(f"fault_flags       : {e.fault_flags or '[]'}")
    print(f"system_fault_esc. : {e.system_fault_escalation}")
    print(f"stamp_status      : {e.stamp_status}")
    print(f"decision_id       : {e.decision_id}")
    print(f"ledger_curr_hash  : {e.ledger_current_hash}")
    if dirs:
        d = dirs[0]
        lifetime_s = (d.expires_at - d.issued_at).total_seconds()
        print("  >> CONTAINMENT DIRECTIVE EMITTED")
        print(
            f"     target          : {d.target_type.value}:{d.target_id}  "
            f"scope={d.scope}"
        )
        print(f"     lifetime        : {lifetime_s:.0f}s  (hard cap 300)")
        print(f"     status          : {d.status.value}")
        print(f"     idempotency_key : {d.idempotency_key}")
        print(f"     live_nc_hash    : {d.live_never_contain_hash}")
    else:
        print("  >> no containment directive — nothing isolated")
    CASE_LOG.append(
        {
            "alert_id": alert_id,
            "label": label,
            "decision_id": e.decision_id,
            "proposed": judgment.proposed_disposition,
            "final": e.final_disposition,
            "host": host,
        }
    )
    return result
"""
        ),
        md(
            """
### Boot

Activate `configs/example_org.yaml` into a throwaway SQLite store.

V2 posture: `containment_policy.default_action: escalate` — containment is **earned**, not granted by omission. Case 1 gets an explicit host allow.
"""
        ),
        code(
            """
def set_host_allow_rules(store, *host_ids: str) -> None:
    # Bind explicit host allow rules under escalate-by-default.
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
    snapshot_hash = compute_snapshot_hash_from_binding(payload)
    updated = base.model_copy(
        update={"containment_policy": policy, "snapshot_hash": snapshot_hash}
    )
    persist_org_config_snapshot(
        store.conn, updated, verbatim_render_text="walkthrough"
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

_tmp = tempfile.TemporaryDirectory(prefix="praetor-walkthrough-")
store = open_state_store(Path(_tmp.name) / "walkthrough.db")
init_annotation_schema(store.conn)
init_policy_gate_evaluation_schema(store.conn)
store.conn.commit()

activate_org_config(
    store, REPO / "configs" / "example_org.yaml", token=SOC_TOKEN, verifier=VERIFIER
)
set_host_allow_rules(store, "WORKSTATION1")
print("activated configs/example_org.yaml")
print("default_action=escalate; explicit allow: WORKSTATION1")
"""
        ),
        # ---- Act I ----
        md(
            """
---

# Act I — The decision thesis

Three alerts. Same engine. Three outcomes.
"""
        ),
        md(
            """
## 1 · Malicious chain → `AUTO_CONTAIN`

`winword.exe` → encoded PowerShell on `WORKSTATION1`. Model proposes contain; gates pass; directive emits.
"""
        ),
        code(
            """
case1 = run_case(
    store,
    alert_id="ALERT-MAL-001",
    bundle=host_evidence("WORKSTATION1", "ev-mal-1", "powershell.exe", "winword.exe"),
    judgment=model_proposes(
        Disposition.AUTO_CONTAIN,
        "ev-mal-1",
        "winword.exe spawned an encoded PowerShell child on WORKSTATION1.",
        ["encoded powershell", "office parent", "off-hours"],
        corroborated=True,
    ),
    label="earned auto_contain",
)
"""
        ),
        md(
            """
**Directive contract:** `host-isolation` · **300s** hard cap · idempotency key · never-contain snapshot hash. Praetor emits; it does not actuate EDR.
"""
        ),
        md(
            """
## 2 · Benign logon → `STANDARD_REVIEW`

Routine interactive shell. Model proposes review; gate agrees; **no directive**.
"""
        ),
        code(
            """
case2 = run_case(
    store,
    alert_id="ALERT-BEN-001",
    bundle=host_evidence("WORKSTATION7", "ev-ben-1", "explorer.exe", "userinit.exe"),
    judgment=model_proposes(
        Disposition.STANDARD_REVIEW,
        "ev-ben-1",
        "Routine interactive logon shell on WORKSTATION7.",
        ["interactive logon", "explorer.exe"],
        corroborated=True,
    ),
    label="safe floor",
)
"""
        ),
        md(
            """
## 3 · Never-contain DC → refuse

Same `auto_contain` proposal on `DC01` (emergency never-contain). Gate overrides → `ESCALATE` / `never_contain_live_conflict`.
"""
        ),
        code(
            """
add_emergency_never_contain(
    store,
    token=SOC_TOKEN,
    verifier=VERIFIER,
    target_specification={"target_type": "host", "target_id": "DC01"},
    lifetime_seconds=3600,
    audit_reason="domain controller — never auto-contain",
)
# Even an explicit allow cannot override live never-contain.
set_host_allow_rules(store, "WORKSTATION1", "DC01")

case3 = run_case(
    store,
    alert_id="ALERT-DC-001",
    bundle=host_evidence("DC01", "ev-dc-1", "powershell.exe", "services.exe"),
    judgment=model_proposes(
        Disposition.AUTO_CONTAIN,
        "ev-dc-1",
        "Suspicious PowerShell on domain controller DC01.",
        ["lsass handle access", "encoded command"],
        corroborated=True,
    ),
    label="never_contain refuse",
)
"""
        ),
        # ---- Act II ----
        md(
            """
---

# Act II — V2 hardening

Containment is earned. Evidence must corroborate. Operators get a feedback loop.
"""
        ),
        md(
            """
## 4 · Thin evidence → `insufficient_corroboration`

V2 host floor (DEC-059): ≥2 distinct provenance paths, ≥1 not attacker-controllable. One citation → escalate, no directive.
"""
        ),
        code(
            """
set_host_allow_rules(store, "WORKSTATION1", "WORKSTATION2")

case4 = run_case(
    store,
    alert_id="ALERT-THIN-001",
    bundle=host_evidence(
        "WORKSTATION2",
        "ev-thin-1",
        "powershell.exe",
        "winword.exe",
        dual_provenance=True,
    ),
    judgment=model_proposes(
        Disposition.AUTO_CONTAIN,
        "ev-thin-1",
        "Single-cited PowerShell on WORKSTATION2 — looks bad, thin evidence.",
        ["encoded powershell"],
        corroborated=False,  # only one provenance cited
    ),
    label="corroboration floor",
)
assert "insufficient_corroboration" in (case4.edict.fault_flags or [])
print("pin: insufficient_corroboration present")
"""
        ),
        md(
            """
## 5 · No allow rule → escalate-by-default

Fully corroborated `auto_contain` on `WORKSTATION9` with **no** matching allow rule. Default `escalate` blocks containment (DEC-058).
"""
        ),
        code(
            """
# Strip allows — only escalate default remains.
set_host_allow_rules(store)  # zero rules

case5 = run_case(
    store,
    alert_id="ALERT-POSTURE-001",
    bundle=host_evidence(
        "WORKSTATION9", "ev-pos-1", "powershell.exe", "winword.exe"
    ),
    judgment=model_proposes(
        Disposition.AUTO_CONTAIN,
        "ev-pos-1",
        "Fully corroborated chain on WORKSTATION9 — but no allow rule.",
        ["encoded powershell", "office parent"],
        corroborated=True,
    ),
    label="escalate-by-default posture",
)
print("pin: containment not granted by omission")
"""
        ),
        md(
            """
## 6 · Progressive authorization report

Read-only rollup of PolicyGate overrides by target type / asset class (V2-032). Intake wiring is a follow-up; here we seed rows from this walkthrough’s decisions.
"""
        ),
        code(
            """
now = datetime.now(UTC)
with critical_transaction(store.conn):
    for i, row in enumerate(CASE_LOG):
        record_policy_gate_evaluation(
            store.conn,
            decision_id=row["decision_id"],
            target_type="host",
            asset_class="workstation" if "DC" not in row["host"] else "domain_controller",
            proposed=row["proposed"],
            final=row["final"],
            evaluated_at=now - timedelta(minutes=len(CASE_LOG) - i),
        )
store.conn.commit()

report = build_progressive_authorization_report(
    store.conn,
    window_start=now - timedelta(hours=1),
    window_end=now + timedelta(minutes=1),
)
print("PROGRESSIVE AUTHORIZATION REPORT (read-only)")
print(f"  read_only={report.read_only}")
for dim in report.policy_gate_by_dimension:
    rate = dim.policy_gate_override_rate
    rate_s = f"{rate:.0%}" if rate is not None else "n/a"
    print(
        f"  {dim.target_type}/{dim.asset_class}: "
        f"evals={dim.policy_gate_evaluations_total} "
        f"overrides={dim.policy_gate_override_total} "
        f"override_rate={rate_s}"
    )
"""
        ),
        md(
            """
## 7 · Similar-case exemplars

Human-confirmed precedents can land in the judgment prompt as illustration-only exemplars (V2-033/034). Not yet wired into production intake — shown via the library API.
"""
        ),
        code(
            """
# Confirm Case 1 as a human-correct precedent (analyst annotation).
with critical_transaction(store.conn):
    submit_annotation(
        store.conn,
        token=ANALYST_TOKEN,
        verifier=VERIFIER,
        decision_id=case1.edict.decision_id,
        disposition_correct=True,
        corrected_disposition=None,
        comment="confirmed macro→powershell intrusion pattern",
        timestamp=datetime.now(UTC),
    )
store.conn.commit()

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
if block:
    exemplars = block.get("exemplars", [])
    print(f"exemplar count: {len(exemplars)}")
    for ex in exemplars:
        print(f"  - {ex.get('exemplar_id')}: {ex.get('disposition')}")
        summary = (ex.get("summary") or "")[:90]
        print(f"    {summary}...")
print("exemplar_scope:", payload["instructions"].get("exemplar_scope", "")[:80], "...")
"""
        ),
        md(
            """
## 8 · Statute curation (review-only)

Annotation-driven `proposed_statute` artifacts are **not activatable** until a SOC lead promotes them (V2-035).
"""
        ),
        code(
            """
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
            source_decision_ids=(case1.edict.decision_id,),
        )
    ],
    source_annotations=[
        SourceAnnotationRef(
            decision_id=case1.edict.decision_id,
            annotation_id=1,
            disposition_correct=True,
            comment="confirmed macro→powershell intrusion pattern",
            reviewer_identity="analyst-1",
            timestamp=datetime.now(UTC),
        )
    ],
    workflow_id="walkthrough-wf-001",
    config_version="statute-proposed-walkthrough",
)
meta = proposed["version_metadata"]
print("artifact_kind     :", meta["artifact_kind"])
print("activation_status :", meta["activation_status"])
yaml_text = render_proposed_statute_yaml(proposed)
try:
    run_preflight(proposed, verbatim_text=yaml_text)
    print("UNEXPECTED: proposed statute passed preflight")
except PreflightError as exc:
    print(f"preflight refused : {exc.code}")
print("pin: proposed_for_review_only")
"""
        ),
        md(
            """
---

## What you saw

| Beat | Outcome |
|---|---|
| 1 Malicious | `AUTO_CONTAIN` + 300s directive |
| 2 Benign | `STANDARD_REVIEW`, no directive |
| 3 Never-contain DC | `ESCALATE` / `never_contain_live_conflict` |
| 4 Thin evidence | `insufficient_corroboration` |
| 5 No allow rule | escalate-by-default blocks contain |
| 6 Progressive report | read-only override rates |
| 7 Exemplars | human-confirmed precedents in prompt |
| 8 Statute curation | `proposed_statute` refused at preflight |

Eval harness: `python -m evals.harness` (32 Outcome-Matrix scenarios). Operator docs: `docs/operator_runbook.md`.
"""
        ),
        code(
            """
store.close()
print("walkthrough store closed")
"""
        ),
    ]

    nb = new_notebook(
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
    nb.nbformat = 4
    nb.nbformat_minor = 5
    return nb


def main() -> None:
    nb = build()
    client = NotebookClient(nb, timeout=180, kernel_name="python3")
    client.execute()
    # Clear transient execution metadata that some renderers dislike; keep outputs.
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.metadata.pop("execution", None)
    nbformat.write(nb, OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
