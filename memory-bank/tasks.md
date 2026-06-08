# Tasks

Index of `docs/plan.md` (35 tasks, 5 sprints).

## Active

| ID | Task | Status | Notes |
|---|---|---|---|
| TASK-013 | Provider abstraction / FakeProvider injection modes | Next | Start Phase 2 after confirming gate artifacts are committed or intentionally left uncommitted |

## Gate prerequisites

- Startup recovery step 6 (idempotency-key, rate-counter, breaker reconciliation)
  is a hard prerequisite for Tasks 17–19; do not implement PolicyGate, rate
  limits, or breakers until this reconciliation is added.
- Add or confirm a regression for `pending_stamp` recovery when no stamp-outbox
  row exists before Task 13 provider work introduces real stamp integrations.

## Upcoming (by phase)

| Phase | Tasks | Pass criteria (summary) |
|---|---|---|
| Phase 2 — Judgment & policy | 13–27 | PolicyGate, eval harness (mandatory scenarios), metrics, reference consumer verifier |
| Phase 3 — Correlation | 28–31 | Real telemetry normalization, identity compliance, correlation gate |
| Phase 4 — Detection portability | 32–33 | Sigma repo, SPL/Splunk demo |
| Phase 5 — Codification & ops | 34–35 | Config sweep prototype, production benchmark, operator runbooks |

Full task definitions, tests-first criteria, and file paths: **`docs/plan.md`**.

## Done

| ID | Task | Evidence |
|---|---|---|
| TASK-001 | Repository structure and test harness | `.workflow/task-001/verification.md` — `pytest` 2 passed; hatchling + Python 3.11+ |
| TASK-002 | Versioned contract models | `.workflow/task-002/verification.md` — 14 models, `schemas/` export, 36 `pytest` passed |
| TASK-003 | Canonical serialization and hash constants | `.workflow/TASK-003/verification.md` — `pytest` 62 passed; `docs/contracts.md` §5/§7; `src/praetor/hashing/` |
| TASK-004 | Authenticated write surface primitives | `.workflow/TASK-004/verification.md` — `pytest` 90 passed; `src/praetor/auth/` |
| TASK-005 | SQLite startup guard and process singleton | `.workflow/TASK-005/verification.md` — `pytest` 107 passed; `src/praetor/runtime/`, `src/praetor/state/sqlite_guard.py` |
| TASK-006 | SQLite state store and attempt lifecycle | `.workflow/TASK-006/verification.md` — `pytest` 152 passed, 32 Task-6 tests; `src/praetor/state/{store,attempts,completed_decisions,idempotency}.py` |
| TASK-007 | Ticket stamp outbox | `.workflow/TASK-007/verification.md` — `pytest` 173 passed, 21 Task-7 tests; reopen hardening pass |
| TASK-008 | SystemHealthAlert outbox | `.workflow/TASK-008/verification.md` — `pytest` 196 passed, 23 Task-8 tests; reopen hardening pass |
| TASK-009 | Org config loader, preflight, activation, emergency never-contain | `.workflow/TASK-009/verification.md` — `pytest` 254 / config 55; contracts §3a; flight recorder closed |
| TASK-010 | Hash-chained audit log and snapshot records | `.workflow/TASK-010/verification.md` — `pytest` 285 / ledger 29; contracts §7a; startup hook |
| TASK-011 | Revocation feed exporter, startup recovery, smoke benchmark | `.workflow/TASK-011/verification.md` — `pytest` 302 / revocation 11; `src/praetor/revocation/` |
| TASK-012 | Walking skeleton decision flow and recovery | `.workflow/TASK-012/verification.md` — `pytest` 341 / engine 25; `src/praetor/engine/` — **Phase 1 gate** |
| PHASE-1-GATE | Gate closure punch-list | `.workflow/phase-1-gate-punchlist.md` — `python -m pytest -q` 343 passed; `python -m mypy src` clean; `python -m ruff check src tests` clean |
