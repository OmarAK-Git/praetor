# Praetor operator runbook

Operational guide for deploying and running Praetor (v1 durable core + V2 hardening). Field-level contract shapes live in generated JSON Schema under `schemas/` (see `docs/contracts.md` §14). This runbook describes behavior, responsibility boundaries, and failure handling — not duplicate schema fields.

## Disposition vocabulary

Praetor uses three final dispositions: `standard_review`, `escalate`, and `auto_contain`. The legacy `pass` label is rejected in all API, schema, enum, and persistence surfaces. Uncertainty routes to `standard_review` (the safe floor). Ticket stamp failure **never** promotes `standard_review` to `escalate`; it preserves the candidate disposition and adds `ticket_stamp_failed`.

## SQLite deployment requirements

Praetor requires a **single-process** deployment with serialized critical paths.

| Parameter | Required value | Enforcement |
|---|---|---|
| `journal_mode` | `WAL` | Startup guard (`run_startup_sqlite_guard`) |
| `synchronous` | at least `NORMAL` (1) | `init_state_dir` bootstrap |
| Connection `isolation_level` | explicit `None` (autocommit) | `open_state_store` |
| Critical mutations | `BEGIN IMMEDIATE` only | `critical_transaction` context manager |
| Process singleton | OS file lock held for lifetime | `SingletonLock` before production intake |

Misconfiguration must exit non-zero before intake opens. Full PRAGMA verification beyond WAL and synchronous is operator responsibility until extended guard checks land; do not run multiple Praetor processes against one state database.

## Startup and recovery order

Before accepting intake (see `docs/spec.md`):

1. Acquire singleton lock.
2. Verify SQLite initialization (WAL, isolation, BEGIN IMMEDIATE discipline).
3. Verify ledger hash-chain integrity — on failure emit `SystemHealthAlert(ledger_chain_integrity_failure)` and refuse start.
4. Recover non-terminal attempts (recovery **never** emits containment).
5. Append safe edicts for stamp-resolved attempts missing ledger rows.
6. Reconcile idempotency keys, rate counters, breakers, and feed outbox rows.
7. Scan outstanding directives against live never-contain; emit revocations and health alerts as needed.
8. Recover pending revocation-feed export rows; if propagation SLO cannot be met, enter **degraded non-actuating mode** (intake may produce `standard_review` or `escalate`, but new `auto_contain` is blocked with `revocation_feed_unhealthy`).
9. Open intake only after reconciliation completes and feed health is within SLO.

## Production throughput ceiling

Sprint 1 defines **provisional** alert-rate targets in org config (`provisional_alert_rate_targets.sustained_alerts_per_minute` and `burst_alerts_per_minute`). These are planning numbers, not guarantees.

### Measurement

Run the production serialized-path benchmark against an activated org config (module entry: benchmarks/serialized_path.py):

```powershell
python -c "from pathlib import Path; from benchmarks.serialized_path import run_serialized_path_benchmark; r = run_serialized_path_benchmark(Path('state/production.db'), operations=30); print(r)"
```

Each **uncontended** iteration (distinct host per alert — best-case ceiling) uses **two** `BEGIN IMMEDIATE` transactions mirroring DEC-053 production intake after a terminal stamp:

1. **PolicyGate evaluation** — `evaluate_policy_gate(..., persist_directive=False)`: feed-health check, live never-contain check, build a *proposed* directive (no exportable emission).
2. **Engine post-stamp commit** — one transaction persisting the deferred directive (idempotency insert, rate-limit update, outstanding directive row), then ledger append (`never_contain_snapshot` + `DecisionEdict`).

No automated revocation or revocation-feed outbox write occurs on this per-alert path. Revocation + feed export throughput is measured separately by `benchmarks/smoke_serialized_path.py` (Task 11).

**Contended path:** duplicate redelivery of the same alert+host suppresses directive emission (`directive_suppressed`) while still appending an edict; the default benchmark rate is an **uncontended, distinct-host best case**. Plan capacity below both numbers for same-host bursts and duplicate intake.

Compare `sustained_alerts_per_minute` to `provisional_alert_rate_targets.sustained_alerts_per_minute`. In v1 the benchmark does **not** measure burst in a separate time window; `meets_burst_target_informational` applies the same sustained rate against the burst target for planning visibility only (`burst_separately_measured=false` on the result).

Every `SerializedPathBenchmarkResult` includes `measurement_context` with hardware (`platform`, `machine`, `processor`, `cpu_count`, `python_version`), scenario (`uncontended_distinct_host` for the default benchmark), and `informational_only=true`. These results are **not production SLAs** — they bound serialized SQLite work on the machine that ran the benchmark.

**Interpretation:** measured rate is an upper bound on serialized SQLite work per distinct host under benchmark conditions (no LLM latency, no stamp outbox, no correlation). Production intake adds provider calls, stamping, and correlation — plan capacity below the measured ceiling.

Example org config defaults: sustained **30**/min, burst **60**/min (`configs/example_org.yaml`).

## LLM failure recovery

Provider failures map to Outcome Matrix dispositions via intake (`process_alert_intake`):

- Malformed JSON, timeout, refusal → `escalate` with appropriate fault flags and `system_fault_escalation` where specified.
- `ProviderUnavailableError` maps to `escalate` with fault flag `provider_unavailable` (`system_fault_escalation=true`, DEC-061) and may also trip the provider-health breaker.

Recovery: fix provider connectivity or configuration; SOC lead may trigger half-open probes (below). Failed judgments do not emit containment.

## Provider-health breaker and half-open probes

Independent domain from containment breaker. When open, production alerts receive `escalate(provider_health_breaker_open)` with `system_fault_escalation=true`.

Recovery paths:

1. **SOC-lead explicit half-open entry** — authenticated action opens probe window.
2. **Timer-based half-open** — after `window_seconds` from open event.

Half-open probes use the synthetic canary payload (`PROVIDER_HEALTH_CANARY_PAYLOAD`) — never real alert data. Probes are rate-limited separately (`probe_rate_limit_per_minute`). Probe failure returns breaker to fully open and resets success countdown. `success_reset_threshold` consecutive probe successes close the breaker.

## Containment breaker

When open, `auto_contain` is blocked; judgment may still yield `escalate` or `standard_review`. Rate-limit counters are **not** modified during an open containment breaker window. Trips emit durable SOC-lead `SystemHealthAlert`s.

## Ledger integrity failure

Startup verifies the hash chain. On break:

- Emit `SystemHealthAlert(ledger_chain_integrity_failure)`.
- Refuse to start intake.
- Operator must restore from backup or follow forensic procedure; do not append new edicts until chain integrity is restored.

The ledger is the audit authority; the revocation feed is a delivery projection only.

## Ledger tail truncation and tip anchor (AG-0027)

The hash chain detects middle deletion and in-place tampering but **cannot detect tail truncation** — deleting the most recent row(s) leaves a prefix that still verifies internally (`verify_ledger_chain()` passes). See `docs/contracts.md` §7a.

### Out-of-band tip anchor procedure

1. **Record anchor** — after each controlled maintenance window or on a periodic schedule, capture the live tip hash from the state database (example using the optional hook's input source):

   ```powershell
   python -c "import sqlite3; from praetor.ledger.store import fetch_ledger_tip_hash; c=sqlite3.connect('state/production.db'); print(fetch_ledger_tip_hash(c))"
   ```

2. **Store anchor** — persist the hex digest in operator-controlled storage **outside** the state DB (WORM volume, HSM audit log, tamper-evident change ticket).

3. **Verify anchor (optional)** — on startup audit or before intake, compare live tip to the last recorded anchor:

   ```powershell
   python -c "import sqlite3; from praetor.ledger.tip_anchor import verify_ledger_tip_against_anchor; c=sqlite3.connect('state/production.db'); verify_ledger_tip_against_anchor(c, expected_tip_hash='<ANCHOR_HEX>')"
   ```

4. **Mismatch response** — tip mismatch indicates tail truncation or unauthorized append since the last anchor. Refuse intake, follow forensic procedure, restore from backup.

The anchor hook is **optional**; Praetor does not require an anchor file at startup unless the deployment enables it.

## Revocation-feed unhealthy mode

When oldest pending feed row age exceeds `max_revocation_feed_propagation_delay_seconds`, or export retries/checksum verification fail, Praetor transitions to `revocation_feed_unhealthy`:

- Emits `SystemHealthAlert(revocation_feed_unhealthy)`.
- PolicyGate blocks **new** `auto_contain` only.
- Alerts whose disposition is `standard_review` or `escalate` on unrelated grounds continue to flow.

Recovery: drain pending feed outbox (`export_pending_feed_rows` at startup / operator-triggered export path). Verify JSONL write ACLs and disk space.

### Feed metadata floor reconciliation (AG-0030)

`last_verified_exported_sequence` in SQLite must not outpace the on-disk `revocation_feed.jsonl`. At startup (`run_feed_startup_hook`) and before each export batch, the exporter reconciles metadata against the physical file via `reconcile_feed_metadata_against_jsonl`. If the file is missing, empty, or truncated relative to metadata, the feed is marked **unhealthy** immediately with no retry budget.

## Feed ACLs and propagation

- **Write:** Praetor runtime principal only (append-only JSONL export).
- **Read:** authorized consumer principals only.
- Propagation SLO measured from `ledger_commit_at` to verified feed write.
- `minimum_feed_sequence_at_issue` on directives is a pre-issuance freshness floor for consumers.

## Feed lag metrics

`MetricsCollector` tracks feed export lag samples (bounded window). Lag is recorded on **export completion** (`export_next_pending_row` / `export_pending_feed_rows` after verified write and `mark_feed_row_exported`), using `ledger_commit_at` to export-finished time — not at intake. Pass an optional `metrics` collector into export functions to populate samples.

Operators should alert when p99 lag approaches `max_revocation_feed_propagation_delay_seconds`. Lag metrics are diagnostic; PolicyGate uses pending row age directly.

## Metrics thread safety

`MetricsCollector` is **not** thread-safe. v1 assumes a single-writer process (the Praetor runtime singleton) mutates metrics; concurrent writers require external synchronization or a future locked implementation.

## Append-only JSONL capacity planning

v1 feed has **no rotation machinery**. Operators must:

1. Size disk for expected revocation volume over directive lifetime + propagation + clock-skew margins.
2. Archive or truncate feed files **only below a retention floor** comfortably greater than directive lifetime + `max_revocation_feed_propagation_delay_seconds` + `max_consumer_clock_skew_seconds`.
3. Never truncate in a way that removes records consumers still need for pre-actuation checks.

**Deferred:** segmented rotation is deferred (see `docs/plan.md` Deferred Work).

Revocation history remains in the hash-chained ledger even when feed files are archived.

## Hash chain as revocation system of record

`DirectiveRevocationRecord` rows in the ledger are authoritative. The JSONL feed is a sequential projection for consumer pre-actuation checks. Audit completeness does not depend on feed file retention if ledger is intact.

## Never-contain conflict after emission

If live never-contain state (including active emergency entries) conflicts with an outstanding directive, startup reconciliation and live checks produce automated `DirectiveRevocationRecord`s and health alerts. Deferred directive persist after stamp re-checks live never-contain; conflict raises `never_contain_live_conflict` and escalates in-band.

## Emergency never-contain race responsibility boundary

Emergency entries are written as `EmergencyNeverContainRecord` by authenticated SOC-lead action. Race window: an emergency entry activated after PolicyGate read but before directive persist is caught by live re-check at persist time (intake deferred persist path). Operators must not assume instantaneous global visibility without reconciliation; startup step 7 scans outstanding directives against current emergency state.

## Stamp recovery

Stamp outbox keyed by stable `stamp_id` (derived from completed-edict three-tuple — see `docs/contracts.md` §5).

| Outcome | Recovery |
|---|---|
| `succeeded` | Append missing edict with `stamp_status=succeeded` |
| `unknown` | Resend same `stamp_id`; idempotent receiver required |
| `failed` | Preserve candidate disposition; add `ticket_stamp_failed`; append one edict |

Redelivery while stamp is in-flight raises `ActiveAttemptExistsError` (DEC-043).

## Non-compliant consumer residual risk

A consumer that skips pre-actuation checks (expiry, embedded never-contain hash, feed freshness, revocation lookup, lineage, or consumer-local policy) may act on stale, revoked, or locally unsafe directives. Praetor supplies signals; **the consumer owns the final actuation decision**. Non-compliant consumers are an operational risk outside Praetor's control boundary.

The reference verifier implements §10 items 1–5 only. **§10 item 6 (consumer-local policy)** is consumer-owned and must be implemented by each integrator before actuation — the reference verifier does not evaluate local policy.

**Named residual window:** a never-contain addition after emission and before a revocation record is published, on a not-yet-expired directive, is not machine-detectable by the consumer. This accepted v1 gap is bounded by the 300-second directive lifetime (see `docs/contracts.md` §10).

**Feed segmentation:** V2 does not ship feed rotation machinery, segment registries, consumer cursor registration, or multi-feed directives. Operators manage append-only JSONL capacity per the runbook; roadmap items remain in `docs/proposals/delivery_backlog.md`.

## Consumer pre-actuation protocol

Compliant consumers must immediately before actuation (see `docs/spec.md`):

1. Confirm clock-sync within `max_consumer_clock_skew_seconds` and directive not expired after skew.
2. Verify embedded never-contain entries hash matches `live_never_contain_hash`.
3. Confirm feed cursor ≥ `minimum_feed_sequence_at_issue` and feed read freshness within propagation + skew bounds.
4. Confirm no revocation for `directive_id` in feed.
5. Confirm no overlapping lineage conflict including supersession.
6. Run any consumer-local policy checks.

Reference implementation: `consumer_sdk/reference_verifier.py`. Schema: `schemas/containment_directive.json`, `schemas/revocation_feed_record.json`.

## Clock skew

`max_consumer_clock_skew_seconds` (org config, default 30) is a deployment prerequisite for consumers, not a universal time guarantee. Directives use short lifetimes (≤5 minutes from issue). Operators must synchronize consumer clocks (NTP) and monitor skew.

## Account containment production feature gate

Production account `auto_contain` requires:

1. Phase 3 identity compliance tests passing on real telemetry shapes.
2. Explicit `account_auto_contain_enabled=true` in org config after gates pass.

Until both hold, account targets receive `escalate(account_containment_disabled)`. Preflight rejects `account_auto_contain_enabled=true` without compliance evidence in v1 Sprint flows — enable only after phase gates documented in `docs/eval_gates.md`.

## Empirical org-config sweep (review-only)

SOC leads can run the sweep CLI against exported Windows telemetry fixtures to produce a **proposed** org-config artifact and markdown coverage report. Output is labeled `artifact_kind: proposed_org_config` and is rejected by activation preflight until a SOC lead promotes it through the normal review path.

```bash
python -m praetor.codification \
  --org-id example-corp \
  --sysmon path/to/sysmon.json \
  --security path/to/security.json \
  --output-yaml proposed_org_config.yaml \
  --output-report sweep_report.md
```

`--sysmon` and `--security` are optional JSON fixture files (envelope `{"events": [...]}` or a bare event list). The CLI exits non-zero on missing files, invalid JSON, blank `--org-id`, or malformed fixture shapes.

**Sweep does not infer policy.** Operators must hand-author before activation:

- **Never-contain exclusions** — sweep emits `REPLACE-BEFORE-ACTIVATION` placeholder targets only; absence of malicious activity is not evidence of safe exclusion.
- **Subnet membership** — observed hosts carry `UNOBSERVED-REQUIRES-HUMAN-REVIEW`; network placement is not derived from v1 telemetry.
- **Containment policy statute** — rate limits, breakers, feed policy, and containment rules copy development defaults; they are not empirically derived.

Run `python -m praetor.codification --help` for the full limitation summary. See `tests/codification/test_sweep.py` for preflight rejection behavior on proposed artifacts.

## Progressive authorization reporting (read-only)

Praetor supports **read-only** progressive authorization reporting for SOC-led authority promotion. Reports aggregate PolicyGate override rate and analyst annotation outcomes by `target_type` and `asset_class` over a chosen time window. They are decision-support only — **no self-tuning, automatic config promotion, or statute mutation** occurs when a report is generated.

### What the report measures

| Signal | Source | Meaning |
|---|---|---|
| PolicyGate override rate | `policy_gate_evaluations` rows | How often the gate changed the model's proposed disposition, per dimension |
| Annotation confirmation rate | `analyst_annotations` joined to evaluations | How often analysts marked the final disposition correct |
| Correction breakdown | Annotations with `disposition_correct=false` | Which corrected dispositions analysts chose per dimension |

Dimensions are `(target_type, asset_class)` — for example `host` + `eng-workstation-pool`. The `asset_class` label is supplied when evaluation rows are recorded (typically from org-config asset grouping at intake time).

### Generating a report

Evaluation rows are persisted automatically during `process_alert_intake` edict commit. Build a windowed report with:

```powershell
python -c "
import sqlite3
from datetime import UTC, datetime, timedelta
from praetor.reporting import build_progressive_authorization_report

conn = sqlite3.connect('state/production.db')
conn.row_factory = sqlite3.Row
end = datetime.now(UTC)
start = end - timedelta(days=7)
report = build_progressive_authorization_report(conn, window_start=start, window_end=end)
print(report)
"
```

The report object exposes `policy_gate_by_dimension` and `annotation_outcomes_by_dimension`. Each dimension includes override rate and annotation confirmation rate helpers. `read_only` is always `True`.

### SOC-led promotion workflow

1. **Review report** — SOC lead reviews override and confirmation rates per asset class and target type over a sustained window (typically multiple weeks).
2. **Decide deliberately** — Promotion widens auto-contain scope (for example adding a containment rule for an asset class) only when measured evidence supports it. Reversal narrows scope when override or incorrect-annotation rates rise.
3. **Propose change** — Draft org-config edits offline or via the sweep CLI proposed artifact path. Do not apply directly to production state.
4. **Activate via existing path** — SOC lead runs normal config activation (`activate_org_config`) with preflight checks and audit trail. This is the **only** sanctioned promotion mechanism.
5. **Record rationale** — Document the report window, dimension metrics, and human decision in the change ticket. The ledger and activation audit remain authoritative.

**Reversal** follows the same path in reverse: SOC lead activates a narrowed config through the audited activation path. Reports do not trigger reversal automatically.

### Explicit non-goals

- Reports do not write org config, containment rules, or never-contain entries.
- Reports do not adjust rate limits, breakers, or model parameters.
- No cron job or threshold hook promotes authority without human activation.

## Statute curation workflow (review-only until activation)

Analyst annotations inform statute edits but **never mutate runtime policy directly**. Praetor formalizes annotation-driven statute changes as a tracked, review-only workflow before SOC-lead promotion.

### Curatable statute sections

SOC leads may propose edits only to these org-config sections:

| Section | Examples |
|---|---|
| `normal_admin_patterns` | Add or refine observed admin behavior patterns |
| `containment_exclusions` | Never-contain target additions or removals |
| `containment_policy` | Widening or narrowing auto-contain scope per asset class |

All other sections (rate limits, breakers, feed policy, principals/assets from sweep) follow existing sweep or hand-edit paths.

### Workflow artifact

`build_statute_curation_workflow` assembles a JSON-serializable artifact capturing:

- **Source annotations** — `decision_id`, annotation id, disposition correctness, analyst comment, reviewer identity, timestamp
- **Proposed edits** — explicit section replacements with rationale and linked decision ids
- **Reviewer** — SOC lead identity assigned at review time (optional until promotion)
- **Proposed config** — review-only YAML with `artifact_kind: proposed_statute` and `activation_status: proposed_for_review_only`
- **Activation audit** — populated only after successful SOC-lead promotion

Serialize for ticket attachment:

```powershell
python -c "
from pathlib import Path
import yaml
from datetime import UTC, datetime
from praetor.codification import (
    SourceAnnotationRef, StatuteEdit, build_statute_curation_workflow,
    render_statute_curation_workflow_json, render_proposed_statute_yaml,
)
from praetor.config.loader import load_org_config_source

base = load_org_config_source(Path('configs/example_org.yaml')).document
patterns = dict(base['normal_admin_patterns'])
patterns['patterns'] = list(patterns['patterns']) + [{
    'name': 'annotation_derived_eng_jumphost',
    'description': 'SOC-confirmed admin pattern from annotation review',
}]
workflow = build_statute_curation_workflow(
    workflow_id='wf-example',
    base_config=base,
    edits=[StatuteEdit(
        section='normal_admin_patterns',
        content=patterns,
        rationale='Annotation evidence supports adding eng jumphost pattern',
        source_decision_ids=('dec-example',),
    )],
    source_annotations=[SourceAnnotationRef(
        decision_id='dec-example',
        annotation_id=1,
        disposition_correct=False,
        comment='model too conservative',
        reviewer_identity='analyst-1',
        timestamp=datetime.now(UTC),
    )],
    config_version='statute-proposed-2.0.0',
    reviewer='soc-lead-1',
)
Path('statute_curation_workflow.json').write_text(
    render_statute_curation_workflow_json(workflow), encoding='utf-8'
)
Path('proposed_statute.yaml').write_text(
    render_proposed_statute_yaml(workflow.proposed_config), encoding='utf-8'
)
"
```

### Review-only preflight guard

Proposed statute artifacts carry `artifact_kind: proposed_statute`. Activation preflight rejects them with `proposed_artifact_not_activatable` — the same fail-closed path as sweep `proposed_org_config` artifacts. Operators must not point production activation at proposed YAML without SOC-lead promotion.

### SOC-lead promotion

Promotion is the **only** path from proposed statute to live config:

1. **Review workflow artifact** — SOC lead validates source annotations, proposed edits, and rendered `proposed_statute.yaml`.
2. **Promote via audited activation** — `promote_statute_curation` strips review-only markers, runs full `activate_org_config` preflight, and records an activation audit trail on the workflow artifact (snapshot hash, reviewer, reconciliation side effects).
3. **Retain audit** — Store the post-promotion workflow JSON alongside the change ticket; `activation_audit` is authoritative for what was activated and when.

```python
from praetor.config.activation import promote_statute_curation

updated_workflow, activation = promote_statute_curation(
    store,
    workflow,
    token=soc_lead_token,
    verifier=verifier,
    output_path=Path("promoted_org_config.yaml"),  # optional audit copy
)
# updated_workflow.activation_audit records snapshot_hash and reviewer
```

### Explicit non-goals

- Annotations do not auto-apply statute edits.
- Proposed statute YAML cannot bypass preflight by activation directly.
- Progressive authorization reports remain read-only decision support (see above); they inform curation but do not promote.

## Phase gates (operator summary)

See `docs/eval_gates.md` for commands. Phase 5 requires empirical org-config sweep review, measured throughput ceiling (this runbook), and Splunk demo reproducibility via the manual procedure in `splunk/README.md` (no automated saved-search validation in CI).

## Related documents

- Architecture overview: `docs/architecture.md`
- Contract meaning and hashes: `docs/contracts.md`
- Generated schemas: `schemas/*.json`
- Product spec: `docs/spec.md` (frozen)
