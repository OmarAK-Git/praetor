# Active Context

## Current focus

**TASK-019 complete** — Provider-health breaker (`praetor.judgment.provider_health_breaker`) trips on production provider failures, emits `provider_health_breaker_open` alerts, supports SOC-lead/timer half-open entry, and runs rate-limited synthetic canary probes with independent metrics.

Next: **TASK-020** (Directive Lifecycle and Revocation). Follow-on: wire production failure recording and PolicyGate into engine intake.

## Recently changed

- TASK-019 gatekeeper: probe-failure cooldown (`opened_at` reset), startup schema via `reconcile_policy_state`, `require_critical_transaction` on half-open transitions, `forbid_during_critical_transaction` on schema init; +10 tests (25 total).
- TASK-019: `src/praetor/judgment/{provider_health_breaker,provider}.py` — half-open probes, canary payload, probe/production metrics; `tests/judgment/` (+15 tests).
- TASK-018: `src/praetor/policy/{rate_limit,circuit_breaker}.py` — multi-scope sliding-window limits, breaker trip/reset, health alert on trip; `tests/policy/` (+10 tests, 39 total).
- TASK-017: `src/praetor/policy/{gate,containment_policy,directive_builder,state}.py` — PolicyGate v1, step 6 reconciliation, `open_production_state_store`.
- TASK-016: account corroboration and identity eligibility.
- Phase 1 punch-list cleared; repo-wide ruff clean.

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- PolicyGate module complete but not wired into `engine/orchestrator.py` intake path.

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** substitute only via `engine/ids.py` / `decision_id_for_attempt`.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Startup order: singleton lock → SQLite guard → `open_state_store` (ledger verify, **engine recovery incl. step 6**, then feed recovery if active config) → intake.
7. Engine intake: `process_alert_intake` still uses skeleton inline policy; call `evaluate_policy_gate` when wiring containment.
8. Rate limits: DEC-029 limit=1/scope/window; DEC-030 `per_asset_group` = host asset_id only; unregistered hosts check `per_host` only.
9. Containment breaker: DEC-031 window-elapse recovery on open-check; in-tx race loss uses `_RateLimitRaceLoss` + committed failure tx.
10. Gate entry calls `init_health_alert_emit_schema` (outbox + pending flush); never `init_policy_state_schema` inside `critical_transaction`.
11. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
