# Praetor architecture

High-level view of Praetor (v1 durable core + V2 hardening) for operators and integrators. **Field-level shapes** are generated to `schemas/` from Pydantic models (`src/praetor/contracts/`). Meaning, derivations, and hash formulas are in `docs/contracts.md` — this document references schemas; it does not duplicate field lists.

## Purpose

Praetor is a post-detection disposition-policy engine: it ingests alerts, correlates local telemetry into an `EvidenceBundle`, obtains a `ModelJudgment` from a provider, runs deterministic `PolicyGate` checks, stamps tickets, and appends hash-chained `DecisionEdict` records. Containment directives are integration contracts for external actuators; Praetor does not directly execute EDR/SOAR actions.

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

Operator-adjacent (V2): reporting · similar-case retrieval · statute curation
```

| Package | Role | Primary schema(s) |
|---|---|---|
| `praetor.contracts` | Versioned domain models | All `schemas/*.json` |
| `praetor.hashing` | Canonical serialization, IDs, feed checksum | `docs/contracts.md` §1–§9 |
| `praetor.runtime` | Singleton lock | — |
| `praetor.state` | SQLite store, attempts, idempotency | — |
| `praetor.config` | Org config load, preflight, activation | `schemas/org_config_snapshot.json` |
| `praetor.correlation` | Sysmon/Security normalization + host isolation | `schemas/evidence_bundle.json` |
| `praetor.judgment` | Provider protocol, prompts, exemplar slot | `schemas/model_judgment.json` |
| `praetor.judgment.agentic` | 3-phase agentic judgment pipeline (opt-in `JudgmentProvider`) | — |
| `praetor.evidence` | Citation validation, host/account corroboration | — |
| `praetor.policy` | PolicyGate, rate limits, breakers, `default_action` | `schemas/policy_gate_result.json`, `schemas/containment_directive.json` |
| `praetor.engine` | Intake orchestrator, recovery | `schemas/decision_edict.json` |
| `praetor.tickets` | Stamp outbox | — |
| `praetor.alerts` | SystemHealthAlert outbox | `schemas/system_health_alert.json` |
| `praetor.ledger` | Hash-chained audit log | ledger record schemas in §14 |
| `praetor.revocation` | Feed exporter | `schemas/revocation_feed_record.json`, `schemas/directive_revocation_record.json` |
| `praetor.metrics` | In-process counters + evaluation recording helpers | `docs/contracts.md` §13 |
| `praetor.reporting` | Progressive authorization reporting (read-only) | — |
| `praetor.retrieval` | Similar-case ranking for prompt exemplars | — |
| `praetor.annotations` | Analyst annotations + human-confirmed precedents | — |
| `praetor.codification` | Org-config sweep, CLI, statute curation (review-only → promote) | — |
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
- Host/account corroboration floors (DEC-059 design; **temporary ≥1 floor DEC-065**)
- Org-config `default_action` / rule precedence (DEC-058)
- Idempotency key insertion

Production intake evaluates gate with `persist_directive=False` until terminal stamp, then persists directive in the same transaction as edict append (DEC-053).

## V2 authorization posture (summary)

- Required `containment_policy.default_action` (example org: `escalate`).
- No matching rule → fall through to `default_action` (implicit default-allow retired).
- Sole matching `escalate` rule blocks `auto_contain`.
- Host `auto_contain` requires corroborated cited evidence per DEC-065 temporary floor (`insufficient_corroboration` on zero anchoring cites or sole ambiguous anchoring cite).
- All production containment authorization flows through PolicyGate (V2-025).

## Detection portability (Phase 4)

Sigma rules under `detections/sigma/` compile to SPL (`tools/compile_sigma.py`). Splunk demo artifacts under `splunk/` — see `splunk/README.md`.

## Codification and statute curation

`praetor.codification.run_org_config_sweep` (CLI: `python -m praetor.codification`) produces **proposed** org-config artifacts rejected by preflight — SOC review only. Statute curation (`proposed_statute`) follows the same review-only → `promote_statute_curation` path (V2-035). See `docs/operator_runbook.md`.

## Progressive reporting and similar-case retrieval

- **Reporting** (`praetor.reporting`): read-only aggregation of PolicyGate overrides + annotations by asset class — SOC-led promotion signal, never auto-tunes config.
- **Retrieval** (`praetor.retrieval`): ranks human-confirmed precedents into a bounded prompt exemplar block outside the evidence hash path.
- Both modules are wired into `process_alert_intake`: evaluation rows persist on edict commit; similar-case exemplars inject into the judgment prompt when precedents exist.

## Benchmarks

| Script | Measures |
|---|---|
| `benchmarks/smoke_serialized_path.py` | Revocation + feed outbox path (Task 11) |
| `benchmarks/serialized_path.py` | DEC-053 production post-stamp path: gate eval (`persist_directive=False`) + engine commit (directive + ledger); distinct-host uncontended best case |

Throughput targets: org config `provisional_alert_rate_targets`. Ceiling interpretation: `docs/operator_runbook.md`.

## Eval and phase gates

Deterministic harness: `evals/harness.py` (32 scenarios). Phase 3 gate: `evals/run_phase3_gate.py`. Correlation gate: `evals/correlation_gate.py`. Details: `docs/eval_gates.md`. V2 Gates 0–5: `.workflow/v2-gate-*-exit/`.

## Explicit non-goals

Horizontal scaling, feed rotation machinery, direct SOAR/EDR adapters, analyst UI beyond annotations, self-tuning containment authority, cloud/Linux telemetry — see `docs/plan.md` Deferred Work and `docs/proposals/v2_implementation_plan.md` Deferred Work.

## Document map

| Document | Audience |
|---|---|
| `docs/prd.md` | Product intent |
| `docs/spec.md` | Frozen v1 behavioral spec |
| `docs/plan.md` | v1 implementation task index |
| `docs/proposals/v2_implementation_plan.md` | V2 task index (complete) |
| `docs/contracts.md` | Hashing, meaning, schema index |
| `docs/decisions.md` | Ratified refinements (DEC-058+) |
| `docs/operator_runbook.md` | Operations |
| `docs/eval_gates.md` | CI and phase gates |
| `schemas/` | Generated field-level contracts |
