# Active Context

## Current focus

**TASK-010 complete (revised)** — hash-chained ledger with `docs/contracts.md` §7a pin, `run_ledger_startup_hook` in `open_state_store`, 29 ledger tests, 285 suite. Next: **TASK-011**.

**Hard gate:** Three role-tagged external surfaces exist; ledger append remains internal-only via `append_ledger_record` inside `critical_transaction`. Startup chain verify exposed as `verify_ledger_chain_at_startup` (full startup wiring in Task 12).

## Recently changed

- TASK-010: `src/praetor/ledger/` — hash chain append/verify, `ledger_chain` SQLite table, startup integrity + health alert; `DecisionEdict.ledger_previous_hash` nullable for genesis.
- TASK-009: `src/praetor/config/` — YAML loader, preflight, snapshot hash, activation + reconciliation, emergency never-contain; `configs/example_org.yaml`.
- TASK-008 reopen: test fakes removed from production; sink exception taxonomy; nested critical-tx boundary; duplicate `alert_id` idempotency; 14 new hardening tests; DEC-026/027.

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- Revocation/emergency paths not yet appending to chain (Task 11–12).

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** preimage exactly `praetor:v1:empty_bundle`; hash baked into correlation-failure IDs.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code — not follow-up tickets.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Domain constants live only in `src/praetor/hashing/domains.py` (includes `DOMAIN_LEDGER_LINK` for chain links).
7. Auth: external surfaces via `authenticate_*` functions; token issuance is operator-supplied (`TokenVerifier` protocol).
8. Startup: acquire `SingletonLock(state_dir)` first; call `init_state_dir(db_path)` once on fresh deploy; then `run_startup_sqlite_guard(db_path, singleton=lock)`; open lifecycle via `open_state_store(db_path)`; critical writes use `critical_transaction(conn)`.
9. State store is v1 single-writer — one process with singleton lock; `allocate_attempt` / revocation paths require that constraint.
10. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
11. Ticket stamp: `derive_stamp_id` from three-tuple; `execute_stamp` writes pending before backend call; transport/timeout ambiguity → `unknown` (not `failed`); recovery resends same `stamp_id` with durable payload; `processing_attempt_identity` is first-writer only (DEC-023).
12. SystemHealthAlert: `emit_system_health_alert` persists pending before delivery; per-channel status in `system_health_delivery_attempts`; v1 channels `jsonl` + `stdout`; failed channels retry via `deliver_health_alerts`; alerts are outbox-only (not hash chain). Duplicate `alert_id` idempotent when payload matches. Must not call persist/emit inside an open `critical_transaction`. JSONL is at-least-once — consumers dedupe on `alert_id`.
13. Org config: `activate_org_config` / `add_emergency_never_contain` require `soc_lead`; verbatim budget on source bytes; binding hash canonical; `org_config_verbatim_renders` per render id; health alerts queued in tx with stable ids and `drain_unflushed_health_alerts` before flush; emergencies/policy reads inside `critical_transaction`.
14. Ledger: `append_ledger_record` requires `critical_transaction`; four interleaved `record_type` values; genesis `ledger_previous_hash=null`; link formula in `docs/contracts.md` §7a; `run_ledger_startup_hook` runs from `open_state_store`; `NeverContainSnapshotRecord.snapshot_hash` must match `compute_never_contain_entries_hash(snapshot_content)`.
