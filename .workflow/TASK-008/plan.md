# Plan: TASK-008

## Goal

Deliver **SystemHealthAlert Outbox** per `docs/plan.md` Task 8 and `docs/spec.md` § SystemHealthAlert Delivery. Critical safety alerts are durable in SQLite before any delivery attempt; v1 delivers to JSONL and stdout with per-channel status tracking; failed channels remain retryable; schema supports future channels without migration.

**Authority:** `docs/spec.md` § SystemHealthAlert Delivery; `docs/plan.md` Task 8; `docs/contracts.md` (SystemHealthAlert contract only). Do not modify `docs/`.

## Scope

**In scope:**

- `src/praetor/alerts/outbox.py` — outbox + per-channel delivery attempt schema, pending write, outcome recording
- `src/praetor/alerts/system_health.py` — emit orchestration (persist → deliver → record), v1 JSONL/stdout sinks
- `src/praetor/alerts/__init__.py` — exports
- `tests/alerts/test_system_health_outbox.py` — all Task 8 test-first criteria
- Minimal `open_state_store` hook to init health alert outbox schema
- Update `tests/contracts/test_scope_guard.py` to allow `alerts` package
- Flight Recorder + Memory Bank updates

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| Ledger chain append | Task 10 |
| Startup recovery enumeration / delivery worker | Task 11–12 |
| Breaker trip / emergency / config activation emitters | Task 9+ |
| SIEM/chat/ticket/SOAR channel implementations | Future; schema only |
| Docs | Any change under `docs/` |

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| REQ-001 | Health alert persisted before delivery attempt | `docs/plan.md` Task 8 |
| REQ-002 | JSONL and stdout delivery statuses recorded per entry | `docs/plan.md` Task 8, `docs/spec.md` |
| REQ-003 | Failed delivery remains retryable | `docs/plan.md` Task 8 |
| REQ-004 | Outbox schema supports future delivery channels without migration | `docs/plan.md` Task 8, `docs/spec.md` |
| REQ-005 | `revocation_feed_unhealthy` alert code supported | `docs/plan.md` Task 8, `docs/spec.md` |
| REQ-006 | SystemHealthAlert records are outbox-only (not in hash chain) | `docs/plan.md` done-when, `docs/spec.md` |
| REQ-007 | Critical writes use `critical_transaction` | Task 5/6/7 pattern |
| REQ-008 | No `docs/` modifications | Scope guard |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema additive table without version bump | Old DBs missing table | `CREATE IF NOT EXISTS` on open; lazy ensure in outbox module |
| Per-channel partial delivery | Alert partially delivered | Track status per channel; retry only pending/failed |
| Scope guard blocks `alerts` package | CI fail | Update guard expected packages for Task 8 |
| stdout testing | Flaky I/O | Inject `TextIO` writer protocol in tests |

## Task breakdown

| ID | Task | Depends on | Notes |
|----|------|------------|-------|
| T-001 | Workflow artifacts | — | plan, traceability, verification, state.json |
| T-002 | Tests first | T-001 | `tests/alerts/test_system_health_outbox.py` |
| T-003 | Implementation | T-002 | outbox.py, system_health.py, store hook |
| T-004 | Verification + Memory Bank | T-003 | pytest, mypy, review, final-report |

## Verification plan (summary)

- `pytest -q` all pass
- `mypy src` pass
- All five Task 8 test-first criteria covered
- Outbox-only confirmed (no ledger tables)
- No `docs/` changes
