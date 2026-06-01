# Plan: TASK-005

## Goal

Deliver **SQLite startup guard and process singleton** per `docs/plan.md` Task 5 and `docs/spec.md` § Durable Lifecycle startup order steps 1–2. A second Praetor process cannot start against the same state directory; WAL misconfiguration exits non-zero; connection isolation is explicit and critical paths use `BEGIN IMMEDIATE`.

**Authority:** `docs/spec.md` § startup order (steps 1–2); `docs/plan.md` Task 5. Do not modify `docs/`.

## Scope

**In scope:**

- `src/praetor/runtime/singleton.py` — OS-level singleton file lock (flock / Windows exclusive lock)
- `src/praetor/state/sqlite_guard.py` — WAL verification, explicit isolation, `BEGIN IMMEDIATE` critical transaction helper
- `tests/runtime/test_startup_guard.py` — all Task 5 test-first criteria
- Update `tests/contracts/test_scope_guard.py` — allow `runtime` and `state` packages
- Flight Recorder + Memory Bank updates

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| State store schema / lifecycle | Task 6 |
| Ledger integrity check | Task 10 / startup step 3 |
| Recovery enumeration | Task 12 |
| Operator runbook | Task 35 (`docs/operator_runbook.md` absent — record gap) |
| Docs | Any change under `docs/` |

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| REQ-001 | Startup fails if singleton file lock cannot be acquired | `docs/plan.md` Task 5 |
| REQ-002 | Startup fails if SQLite journal mode is not WAL | `docs/plan.md` Task 5, `docs/spec.md` |
| REQ-003 | Connection isolation is explicit (not default) | `docs/plan.md` Task 5, `docs/spec.md` |
| REQ-004 | `BEGIN IMMEDIATE` enforced on critical paths | `docs/plan.md` Task 5, `docs/spec.md` |
| REQ-005 | Lock held through process lifetime | `docs/plan.md` Task 5 |
| REQ-006 | Second process cannot start against same state dir | `docs/plan.md` Task 5 |
| REQ-007 | No `docs/` modifications | Scope guard |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| `operator_runbook.md` absent — exact PRAGMA list unspecified | Ambiguous required SQLite params | Implement minimal spec-supported checks (WAL, isolation, BEGIN IMMEDIATE); record gap |
| Windows vs POSIX lock semantics differ | Flaky cross-platform tests | Platform branches in singleton; subprocess test for second-process |
| Task 6 may need different connection API | Rework | Export stable primitives; Task 6 builds on `create_guarded_connection` / `critical_transaction` |

## Task breakdown

| ID | Task | Depends on | Notes |
|----|------|------------|-------|
| T-001 | Workflow artifacts | — | plan, traceability, verification |
| T-002 | Tests first | T-001 | `tests/runtime/test_startup_guard.py` |
| T-003 | `singleton.py` + `sqlite_guard.py` | T-002 | Implement to pass tests |
| T-004 | Scope guard update | T-003 | Allow `runtime`, `state` |
| T-005 | Verification + Memory Bank | T-004 | pytest, review, final-report |

## Verification plan (summary)

- `pytest -q` all pass
- All Task 5 test-first criteria covered
- Scope guard allows `runtime`/`state`, forbids Task 6+ packages
- Record operator-runbook PRAGMA gap in review.md
