# Active Context

## Current focus

**Phase 1 gate cleared** — durable walking skeleton, ledger append coverage, stamp integration, revocation feed, org config, and startup recovery are verified.

Next: **TASK-013** (provider abstraction / FakeProvider).

## Recently changed

- README updated with phase structure, Phase 1 status, built-so-far summary, and browse/demo guidance.
- Phase 1 punch-list cleared: live emergency records/revocations and activation revocations now append to the hash-chain ledger; guarded `open_state_store(..., singleton=...)` fails closed when the singleton/WAL guard is not satisfied; repo-wide ruff is clean.
- TASK-012: `src/praetor/engine/` — hardcoded bundle/judgment intake, fault paths (`correlation_failure`, `config_over_budget`, `invalid_model_citation`), `run_engine_startup_recovery` wired in `open_state_store`; no recovery `auto_contain`.
- TASK-011: revocation feed JSONL exporter, startup recovery hook, feed-health probes, smoke benchmark.
- TASK-010: hash-chained ledger, startup integrity hook.

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- PolicyGate not yet implemented (Task 17); skeleton policy inline only.
- Startup recovery step 6 is not implemented and is a hard prerequisite for Tasks 17-19.

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** substitute only via `engine/ids.py` / `decision_id_for_attempt`.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Startup order: singleton lock → SQLite guard → `open_state_store` (ledger verify, **engine recovery**, then feed recovery if active config) → intake.
7. Engine intake: `process_alert_intake` / `WalkingSkeletonEngine` after active org config; never emits `auto_contain` in v1 skeleton.
8. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
