# Tasks

Index of `docs/plan.md` (35 tasks, 5 sprints).

## Active

| ID | Task | Status | Notes |
|---|---|---|---|
| TASK-008 | SystemHealthAlert outbox | pending | |
| TASK-009 | Org config loader, preflight, activation, emergency never-contain | pending | |
| TASK-010 | Hash-chained audit log and snapshot records | pending | |
| TASK-011 | Revocation feed outbox, exporter, startup recovery, smoke benchmark | pending | |
| TASK-012 | Walking skeleton decision flow and recovery | pending | **Phase 1 gate** ends here |

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
