# Active Context

## Current focus

**TASK-024 complete** — `metrics/{collector,events}.py` in-process collector covers all Task 24 criteria (dispositions, overrides, LLM faults, directives, queue aging, independent breaker/probe domains, stamp/health-alert counters, feed lag p99 + unhealthy transitions).

Next: **TASK-025** (Analyst Annotation Storage). Follow-on: wire `MetricsCollector` into intake/export paths.

## Recently changed

- TASK-024: `metrics/{collector,events}.py` — in-process metrics collector with independent breaker/probe domains, feed lag p99 + warning threshold; 13 metrics tests; suite **556**.
- TASK-023: `tickets/contract.py` — stamp success/failure disposition sequencing; orchestrator in-flight defer; recovery delegation; 14 sequencing tests.
- TASK-022: `engine/{timeouts,queue_policy}.py` — latency SLA tracking, queue age from org config; orchestrator + recovery wiring; 14 engine tests.
- TASK-021 gatekeeper: expiry skew fail-closed (DEC-037); superseded-directive hole; feed checksum; truncation-tolerant gap (DEC-038); revocations in hand; `py.typed` + mypy consumer_sdk; +11 tests (24 consumer_sdk total).

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- PolicyGate module complete but not wired into `engine/orchestrator.py` intake path (stamp contract wired on skeleton path).
- Metrics collector implemented but not wired into production call sites (DEC-046: single-writer when wired).

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
