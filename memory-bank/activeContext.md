# Active Context

## Current focus

**TASK-022 complete** — `engine/timeouts.py` and `engine/queue_policy.py` implement provider latency SLA tracking and queue-aging detection; intake and recovery emit distinct Outcome Matrix fault flags with `system_fault_escalation=true`.

Next: **TASK-023** (Ticket Stamp Contract Integration). Follow-on: wire PolicyGate into engine intake.

## Recently changed

- TASK-022: `engine/{timeouts,queue_policy}.py` — latency SLA tracking, queue age from org config; orchestrator + recovery wiring; 14 engine tests.
- TASK-021 gatekeeper: expiry skew fail-closed (DEC-037); superseded-directive hole; feed checksum; truncation-tolerant gap (DEC-038); revocations in hand; `py.typed` + mypy consumer_sdk; +11 tests (24 consumer_sdk total).
- TASK-021: `consumer_sdk/reference_verifier.py` — §10 ordered checks (clock, expiry, hash, feed floor/staleness/gap, revocation, lineage); 13 tests.
- TASK-020 gatekeeper: manual revocation appends ledger in same tx (DEC-034); builder requires critical_transaction; mid-export feed-floor tests; emergency atomicity hook; +7 tests (23 containment total: lifecycle 15, revocation 8).
- TASK-020: `src/praetor/containment/{lifecycle,revocation}.py` — emit on persist, revocation helpers, refactored activation/emergency/recovery/gate.

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- PolicyGate module complete but not wired into `engine/orchestrator.py` intake path (latency/queue flags wired via skeleton escalate path).

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** substitute only via `engine/ids.py` / `decision_id_for_attempt`.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Startup order: singleton lock → SQLite guard → `open_state_store` (ledger verify, **engine recovery incl. step 6**, then feed recovery if active config) → intake.
7. Engine intake: queue aging checked in recovery for ALLOCATED/ACTIVE only (DEC-040); provider latency tracked after successful provider return.
8. Provider latency SLA: DEC-039 end-to-end retry loop timing; v1 provisional constant 30s.
9. Rate limits: DEC-029 limit=1/scope/window; DEC-030 `per_asset_group` = host asset_id only.
10. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
