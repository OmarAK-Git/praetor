# Active Context

## Current focus

**TASK-020 complete** — `praetor.containment` consolidates directive lifecycle (proposed→emitted on persist) and differentiated revocation triggers (manual, never-contain conflict, post-activation, supersession API).

Next: **TASK-021** (Reference Consumer Verifier). Follow-on: wire production failure recording and PolicyGate into engine intake.

## Recently changed

- TASK-020 gatekeeper: manual revocation appends ledger in same tx (DEC-034); builder requires critical_transaction; mid-export feed-floor tests; emergency atomicity hook; +7 tests (23 containment total: lifecycle 15, revocation 8).
- TASK-020: `src/praetor/containment/{lifecycle,revocation}.py` — emit on persist, revocation helpers, refactored activation/emergency/recovery/gate.
- TASK-019 gatekeeper: probe-failure cooldown, startup schema via `reconcile_policy_state`, tx guards; +10 tests (25 judgment provider-health tests).
- TASK-018: `src/praetor/policy/{rate_limit,circuit_breaker}.py` — multi-scope sliding-window limits, breaker trip/reset.
- TASK-017: PolicyGate v1, step 6 reconciliation, `open_production_state_store`.

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
8. Rate limits: DEC-029 limit=1/scope/window; DEC-030 `per_asset_group` = host asset_id only.
9. Containment breaker: DEC-031 window-elapse recovery on open-check.
10. Gate entry calls `init_health_alert_emit_schema`; directive emit uses `containment.lifecycle.insert_outstanding_directive_in_transaction`.
11. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
