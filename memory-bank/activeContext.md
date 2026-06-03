# Active Context

## Current focus

**TASK-009 complete** — org config loader, preflight, activation, emergency never-contain (55 config tests, 254 suite). Next: **TASK-010** hash-chained ledger.

**Hard gate:** Three role-tagged external surfaces exist; ledger/feed/directive emission remain internal-only. Startup singleton + WAL guard operational.

## Recently changed

- TASK-009: `src/praetor/config/` — YAML loader, preflight, snapshot hash, activation + reconciliation, emergency never-contain; `configs/example_org.yaml`.
- TASK-008 reopen: test fakes removed from production; sink exception taxonomy; nested critical-tx boundary; duplicate `alert_id` idempotency; 14 new hardening tests; DEC-026/027.
- TASK-008: `src/praetor/alerts/{outbox,system_health}.py` — durable health alert outbox; per-channel delivery; JSONL + stdout v1 sinks.
- TASK-007 reopen: ambiguous backend errors → `unknown`; 10 new hardening tests; DEC-023 processing_attempt_identity semantics.
- TASK-007: `src/praetor/tickets/{outbox,stamp}.py` — durable stamp outbox keyed by `stamp_id`.
- TASK-006: `src/praetor/state/{store,attempts,completed_decisions,idempotency}.py` — attempt lifecycle, completed-edict three-tuple, revocation + feed outbox.

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- Provisional alert-rate targets validated in org-config preflight (Task 9); eval harness wiring remains Tasks 11+.

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** preimage exactly `praetor:v1:empty_bundle`; hash baked into correlation-failure IDs.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code — not follow-up tickets.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Domain constants live only in `src/praetor/hashing/domains.py`.
7. Auth: external surfaces via `authenticate_*` functions; token issuance is operator-supplied (`TokenVerifier` protocol).
8. Startup: acquire `SingletonLock(state_dir)` first; call `init_state_dir(db_path)` once on fresh deploy; then `run_startup_sqlite_guard(db_path, singleton=lock)`; open lifecycle via `open_state_store(db_path)`; critical writes use `critical_transaction(conn)`.
9. State store is v1 single-writer — one process with singleton lock; `allocate_attempt` / revocation paths require that constraint.
10. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
11. Ticket stamp: `derive_stamp_id` from three-tuple; `execute_stamp` writes pending before backend call; transport/timeout ambiguity → `unknown` (not `failed`); recovery resends same `stamp_id` with durable payload; `processing_attempt_identity` is first-writer only (DEC-023).
12. SystemHealthAlert: `emit_system_health_alert` persists pending before delivery; per-channel status in `system_health_delivery_attempts`; v1 channels `jsonl` + `stdout`; failed channels retry via `deliver_health_alerts`; alerts are outbox-only (not hash chain). Duplicate `alert_id` idempotent when payload matches. Must not call persist/emit inside an open `critical_transaction`. JSONL is at-least-once — consumers dedupe on `alert_id`.
13. Org config: `activate_org_config` / `add_emergency_never_contain` require `soc_lead`; verbatim budget on source bytes; binding hash canonical; `org_config_verbatim_renders` per render id; health alerts queued in tx with stable ids and `drain_unflushed_health_alerts` before flush; emergencies/policy reads inside `critical_transaction`.
