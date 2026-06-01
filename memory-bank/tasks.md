# Tasks

Index of `docs/plan.md` (35 tasks, 5 sprints). Status reflects repo state: **no implementation started**.

## Active

| ID | Task | Status | Notes |
|---|---|---|---|
| TASK-001 | Repository structure and test harness | pending | Sprint 1; `pyproject.toml`, `src/praetor/`, `pytest`, fixture manifest |
| TASK-002 | Versioned contract models | pending | Depends on 001; Pydantic models + `schemas/` export |
| TASK-003 | Canonical serialization and hash constants | pending | **Blocked on:** treat `docs/contracts.md` as fixed; implement per doc |
| TASK-004 | Authenticated write surface primitives | pending | soc_lead / analyst roles; three external surfaces |
| TASK-005 | SQLite startup guard and process singleton | pending | WAL, singleton lock |
| TASK-006 | SQLite state store and attempt lifecycle | pending | |
| TASK-007 | Ticket stamp outbox | pending | |
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
| — | — | — |
