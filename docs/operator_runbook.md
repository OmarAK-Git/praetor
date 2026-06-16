# Praetor operator runbook

Operational guide for deploying and running Praetor v1. Field-level contract shapes live in generated JSON Schema under `schemas/` (see `docs/contracts.md` §14). This runbook describes behavior, responsibility boundaries, and failure handling — not duplicate schema fields.

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

**Interpretation:** measured rate is an upper bound on serialized SQLite work per distinct host under benchmark conditions (no LLM latency, no stamp outbox, no correlation). Production intake adds provider calls, stamping, and correlation — plan capacity below the measured ceiling.

Example org config defaults: sustained **30**/min, burst **60**/min (`configs/example_org.yaml`).

## LLM failure recovery

Provider failures map to Outcome Matrix dispositions via intake (`process_alert_intake`):

- Malformed JSON, timeout, refusal → `escalate` with appropriate fault flags and `system_fault_escalation` where specified.
- Provider unavailable may trip the provider-health breaker when wired; intake catch for `ProviderUnavailableError` remains environment-specific.

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

## Revocation-feed unhealthy mode

When oldest pending feed row age exceeds `max_revocation_feed_propagation_delay_seconds`, or export retries/checksum verification fail, Praetor transitions to `revocation_feed_unhealthy`:

- Emits `SystemHealthAlert(revocation_feed_unhealthy)`.
- PolicyGate blocks **new** `auto_contain` only.
- Alerts whose disposition is `standard_review` or `escalate` on unrelated grounds continue to flow.

Recovery: drain pending feed outbox (`export_pending_feed_rows` at startup / operator-triggered export path). Verify JSONL write ACLs and disk space.

## Feed ACLs and propagation

- **Write:** Praetor runtime principal only (append-only JSONL export).
- **Read:** authorized consumer principals only.
- Propagation SLO measured from `ledger_commit_at` to verified feed write.
- `minimum_feed_sequence_at_issue` on directives is a pre-issuance freshness floor for consumers.

## Feed lag metrics

`MetricsCollector` tracks feed export lag samples (bounded window). Operators should alert when p99 lag approaches `max_revocation_feed_propagation_delay_seconds`. Lag metrics are diagnostic; PolicyGate uses pending row age directly.

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

A consumer that skips pre-actuation checks (expiry, embedded never-contain hash, feed freshness, revocation lookup, lineage) may act on stale, revoked, or locally unsafe directives. Praetor supplies signals; **the consumer owns the final actuation decision**. Non-compliant consumers are an operational risk outside Praetor's control boundary.

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

## Phase gates (operator summary)

See `docs/eval_gates.md` for commands. Phase 5 requires empirical org-config sweep review, measured throughput ceiling (this runbook), and Splunk demo reproducibility via the manual procedure in `splunk/README.md` (no automated saved-search validation in CI).

## Related documents

- Architecture overview: `docs/architecture.md`
- Contract meaning and hashes: `docs/contracts.md`
- Generated schemas: `schemas/*.json`
- Product spec: `docs/spec.md` (frozen)
