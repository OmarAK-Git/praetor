# Praetor architecture

High-level view of Praetor v1 for operators and integrators. **Field-level shapes** are generated to `schemas/` from Pydantic models (`src/praetor/contracts/`). Meaning, derivations, and hash formulas are in `docs/contracts.md` — this document references schemas; it does not duplicate field lists.

## Purpose

Praetor is a post-detection disposition-policy engine: it ingests alerts, correlates local telemetry into an `EvidenceBundle`, obtains a `ModelJudgment` from a provider, runs deterministic `PolicyGate` checks, stamps tickets, and appends hash-chained `DecisionEdict` records. Containment directives are integration contracts for external actuators; Praetor does not directly execute EDR/SOAR actions in v1.

## Disposition model

| Disposition | Meaning |
|---|---|
| `standard_review` | Route to human review (safe default; replaces legacy `pass`) |
| `escalate` | Immediate human attention; may carry fault flags |
| `auto_contain` | Emit `ContainmentDirective` when all deterministic gates pass |

## Major subsystems

```
Alert intake → Correlation → Judgment (LLM) → PolicyGate → Stamp → Ledger
                                    ↓
                          ContainmentDirective → Revocation feed (JSONL projection)
                                    ↓
                          Consumer pre-actuation (external)
```

| Package | Role | Primary schema(s) |
|---|---|---|
| `praetor.contracts` | Versioned domain models | All `schemas/*.json` |
| `praetor.hashing` | Canonical serialization, IDs, feed checksum | `docs/contracts.md` §1–§9 |
| `praetor.runtime` | Singleton lock | — |
| `praetor.state` | SQLite store, attempts, idempotency | — |
| `praetor.config` | Org config load, preflight, activation | `schemas/org_config_snapshot.json` |
| `praetor.correlation` | Sysmon/Security normalization | `schemas/evidence_bundle.json` |
| `praetor.judgment` | Provider protocol, prompts | `schemas/model_judgment.json` |
| `praetor.evidence` | Citation validation | — |
| `praetor.policy` | PolicyGate, rate limits, breakers | `schemas/policy_gate_result.json`, `schemas/containment_directive.json` |
| `praetor.engine` | Intake orchestrator, recovery | `schemas/decision_edict.json` |
| `praetor.tickets` | Stamp outbox | — |
| `praetor.alerts` | SystemHealthAlert outbox | `schemas/system_health_alert.json` |
| `praetor.ledger` | Hash-chained audit log | ledger record schemas in §14 |
| `praetor.revocation` | Feed exporter | `schemas/revocation_feed_record.json`, `schemas/directive_revocation_record.json` |
| `praetor.metrics` | In-process counters | `docs/contracts.md` §13 |
| `praetor.codification` | Empirical org-config sweep (review-only artifacts) | — |
| `consumer_sdk` | Reference consumer verifier | — |

## Durable boundaries

- **Ledger** — system of record for edicts, revocations, never-contain snapshots, emergencies.
- **Revocation feed** — append-only JSONL projection for consumer freshness; not authoritative for audit.
- **Stamp outbox** — ticketing integration boundary; precedes ledger append.
- **Health alert outbox** — durable SOC notifications.

## Startup singleton path

One process holds `SingletonLock` and opens `StateStore` with WAL verification. Production entrypoint: `open_production_state_store`. Recovery never emits containment (see `docs/operator_runbook.md`).

## PolicyGate transaction

For proposed `auto_contain`, gate evaluation and (when enabled) directive persist occur inside `BEGIN IMMEDIATE` transactions with:

- Revocation-feed health (pending row age vs propagation SLO)
- Live never-contain + emergency entries
- Rate limits and containment breaker state
- Idempotency key insertion

Production intake evaluates gate with `persist_directive=False` until terminal stamp, then persists directive in the same transaction as edict append (DEC-053).

## Detection portability (Phase 4)

Sigma rules under `detections/sigma/` compile to SPL (`tools/compile_sigma.py`). Splunk demo artifacts under `splunk/` — see `splunk/README.md`.

## Codification (Phase 5)

`praetor.codification.run_org_config_sweep` produces **proposed** org-config artifacts (`artifact_kind: proposed_org_config`) rejected by preflight — SOC review only.

## Benchmarks

| Script | Measures |
|---|---|
| `benchmarks/smoke_serialized_path.py` | Revocation + feed outbox path (Task 11) |
| `benchmarks/serialized_path.py` | DEC-053 production post-stamp path: gate eval (`persist_directive=False`) + engine commit (directive + ledger); distinct-host uncontended best case |

Throughput targets: org config `provisional_alert_rate_targets`. Ceiling interpretation: `docs/operator_runbook.md`.

## Eval and phase gates

Deterministic harness: `evals/harness.py`. Phase 3 gate: `evals/run_phase3_gate.py`. Correlation gate: `evals/correlation_gate.py`. Details: `docs/eval_gates.md`.

## Explicit non-goals (v1)

Horizontal scaling, feed rotation machinery, direct SOAR/EDR adapters, analyst UI beyond annotations, subnet/asset-group containment, cloud/Linux telemetry — see `docs/plan.md` Deferred Work.

## Document map

| Document | Audience |
|---|---|
| `docs/prd.md` | Product intent |
| `docs/spec.md` | Frozen behavioral spec |
| `docs/plan.md` | Implementation task index |
| `docs/contracts.md` | Hashing, meaning, schema index |
| `docs/decisions.md` | Ratified refinements |
| `docs/operator_runbook.md` | Operations |
| `docs/eval_gates.md` | CI and phase gates |
| `schemas/` | Generated field-level contracts |
