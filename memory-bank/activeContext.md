# Active Context

## Current focus

**TASK-018 complete** — Transactional rate limits (`praetor.policy.rate_limit`) enforce per-host/subnet/asset-group sliding windows; containment circuit breaker (`praetor.policy.circuit_breaker`) trips on rate-limit failures, emits health alerts, and freezes counters while open.

Next: **TASK-019** (Provider-Health Breaker with Half-Open Probes). Follow-on: wire PolicyGate into engine intake (orchestrator still uses skeleton inline policy).

## Recently changed

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
