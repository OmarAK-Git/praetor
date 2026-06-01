# Plan: TASK-006

## Goal

Deliver **SQLite state store and attempt lifecycle** per `docs/plan.md` Task 6 and `docs/spec.md` § Durable Lifecycle. The state store is authoritative for per-alert side effects: one non-terminal attempt per `alert_identity`, completed-edict uniqueness on the three-tuple, correct state transitions, aborted attempts not blocking changed-input retries, and revocation writes (`DirectiveRevocationRecord` + feed outbox row + idempotency key clear or retain) in one `critical_transaction`.

**Authority:** `docs/spec.md` § Durable Lifecycle; `docs/plan.md` Task 6; `docs/contracts.md` §3–§6, §11. Do not modify `docs/`.

## Scope

**In scope:**

- `src/praetor/state/store.py` — schema init, `StateStore`, revocation + feed outbox inserts
- `src/praetor/state/attempts.py` — attempt states, allocation, transitions
- `src/praetor/state/completed_decisions.py` — three-tuple lookup and insert
- `src/praetor/state/idempotency.py` — active keys and clear-on-manual-revocation
- `tests/state/test_attempt_lifecycle.py` — all Task 6 test-first criteria
- Update `src/praetor/state/__init__.py` exports
- Flight Recorder + Memory Bank updates

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| Ticket stamp outbox | Task 7 |
| SystemHealthAlert outbox | Task 8 |
| Org config loader / activation | Task 9 |
| Hash-chained ledger append | Task 10 (revocation rows stored durably; chain append later) |
| Feed JSONL exporter / startup recovery | Task 11–12 |
| Docs | Any change under `docs/` |

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| REQ-001 | At most one non-terminal attempt per `alert_identity` | `docs/plan.md` Task 6, `docs/spec.md`, `docs/contracts.md` §6 |
| REQ-002 | Duplicate-intake loser re-checks completed edict after lock | `docs/contracts.md` §6 |
| REQ-003 | Completed-edict uniqueness on alert/bundle/config three-tuple | `docs/spec.md`, `docs/contracts.md` §6 |
| REQ-004 | Attempt states transition per lifecycle FSM | `docs/spec.md` |
| REQ-005 | Aborted attempts do not block future changed-input attempts | `docs/plan.md` Task 6 |
| REQ-006 | SOC-lead manual revocation: record + feed outbox + idempotency clear in one tx | `docs/plan.md` Task 6, `docs/spec.md` § DirectiveRevocationRecord |
| REQ-007 | Automated revocation: record + feed outbox; idempotency key not cleared | `docs/plan.md` Task 6 |
| REQ-008 | Critical paths use `critical_transaction` (BEGIN IMMEDIATE) | `docs/spec.md`, Task 5 |
| REQ-009 | Single-writer deployment constraint documented in code/Memory Bank | `docs/plan.md` Task 6 done-when |
| REQ-010 | No `docs/` modifications | Scope guard |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ledger append not in Task 6 | Revocation not on hash chain yet | Store `DirectiveRevocationRecord` JSON + feed outbox; Task 10 chains |
| `foreign_keys` PRAGMA unspecified in runbook | Schema integrity | Enable `PRAGMA foreign_keys=ON` at connection open; record gap |
| Serializable vs IMMEDIATE wording | Wrong isolation | Use Task 5 `critical_transaction`; spec serializable satisfied by single-writer + IMMEDIATE |
| Feed export logic in Task 11 | Incomplete revocation path | Outbox row + gap-free `sequence_number` assignment only |

## Task breakdown

| ID | Task | Depends on | Notes |
|----|------|------------|-------|
| T-001 | Workflow artifacts | — | plan, traceability, verification, state.json |
| T-002 | Tests first | T-001 | `tests/state/test_attempt_lifecycle.py` |
| T-003 | Schema + modules | T-002 | store, attempts, completed_decisions, idempotency |
| T-004 | Verification + Memory Bank | T-003 | pytest, mypy, review, final-report |

## Verification plan (summary)

- `pytest -q` all pass
- `mypy src` pass
- All seven Task 6 test-first criteria covered
- No `docs/` changes
- Record ledger-append and full startup-recovery gaps in review.md
