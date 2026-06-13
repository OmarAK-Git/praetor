# Active Context

## Current focus

**TASK-023 complete** (gatekeeper 2026-06-13) — `tickets/contract.py` stamp failure preserves candidate row + appends `ticket_stamp_failed`; redelivery during in-flight stamp raises `ActiveAttemptExistsError`.

Next: **TASK-024** (Metrics). Follow-on: wire PolicyGate into engine intake.

## Recently changed

- TASK-023: `tickets/contract.py` — stamp success/failure disposition sequencing; orchestrator in-flight defer; recovery delegation; 14 sequencing tests.
- TASK-022: `engine/{timeouts,queue_policy}.py` — latency SLA tracking, queue age from org config; orchestrator + recovery wiring; 14 engine tests.
- TASK-021 gatekeeper: expiry skew fail-closed (DEC-037); superseded-directive hole; feed checksum; truncation-tolerant gap (DEC-038); revocations in hand; `py.typed` + mypy consumer_sdk; +11 tests (24 consumer_sdk total).

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- PolicyGate module complete but not wired into `engine/orchestrator.py` intake path (stamp contract wired on skeleton path).

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** substitute only via `engine/ids.py` / `decision_id_for_attempt`.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Startup order: singleton lock → SQLite guard → `open_state_store` (ledger verify, **engine recovery incl. step 6**, then feed recovery if active config) → intake.
7. Stamp contract: failure preserves full candidate row + appends `ticket_stamp_failed`; in-flight (`pending`/`unknown`) defers ledger append; redelivery raises `ActiveAttemptExistsError` (DEC-043).
8. Provider latency SLA: DEC-039 end-to-end retry loop timing; v1 provisional constant 30s.
9. Rate limits: DEC-029 limit=1/scope/window; DEC-030 `per_asset_group` = host asset_id only.
10. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
