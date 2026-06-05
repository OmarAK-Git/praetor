# Verification Ledger: TASK-012

Re-run 2026-06-05 after review-driven hardening (single-site EMPTY_BUNDLE, recovery tests, docstring/step-6 correction).

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | Walking-skeleton intake + fault paths | Unit | `pytest -q tests/engine/test_walking_skeleton.py` | pass | 5 passed | pass |
| VERIFY-002 | Crash/startup recovery | Unit | `pytest -q tests/engine/test_crash_recovery.py` | pass | 18 passed | pass |
| VERIFY-003 | EMPTY_BUNDLE single-site invariant | Unit | `pytest -q tests/engine/test_engine_ids.py` | pass | 2 passed | pass |
| VERIFY-004 | Engine subtotal | Unit | `pytest -q tests/engine/` | pass | 25 passed | pass |
| VERIFY-005 | Full suite | Regression | `pytest -q` | pass | 341 passed | pass |
| VERIFY-006 | Types | mypy | `mypy src` | OK | 66 files OK | pass |
| VERIFY-007 | Lint | ruff | `ruff check src/praetor/engine tests/engine` | pass | All checks passed | pass |
| VERIFY-008 | Scope | guard | `tests/contracts/test_scope_guard.py` (in suite) | engine allowed | pass | pass |
| VERIFY-009 | No docs edits | git | `git diff --name-only docs/` | empty | empty | pass |

**Status values:** `pending` | `pass` | `fail` | `skipped`

## Review-driven coverage added (2026-06-05)

| Check | Test | Covers |
|---|---|---|
| Crash window: edict appended, attempt not completed | `test_crash_window_edict_appended_attempt_not_completed_does_not_duplicate` | spec step 5 anti-duplicate (`ledger_has_edict_for_decision_id` True branch) |
| Unresolvable UNKNOWN stamp | `test_unresolvable_unknown_stamp_aborts_attempt_without_edict` | `_ensure_terminal_stamp` None → abort, no edict |
| Failed stamp, auto_contain candidate | `test_failed_stamp_with_autocontain_candidate_downgrades_to_escalate` | pinned override (recovery never emits containment) |
| Correlation-failure redelivery | `test_correlation_failure_redelivery_produces_second_edict` | pinned behavior: no three-tuple dedup row on abort |
| Stored bundle hash == decision_id input | `test_stored_bundle_hash_equals_decision_id_input` | §3.3 single-substitution-site |
| Directive-scan idempotency + alert-id list | `test_startup_directive_scan_is_idempotent` | one revocation/feed/ledger/alert; returned ids only conflict |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Schema export regen | No contract model changes | Low |
| Full `verify_ledger_chain` on engine-appended rows | Chain continuity rests on `append_ledger_record` (Task 10, verified there); audit link verified via snapshot pairing | Low |
| Startup step 6 (idempotency/rate/breaker reconciliation) | No v1 containment to reconcile; owned by PolicyGate/breaker tasks | Low (documented in code + review) |

## Summary

- **Last run:** 2026-06-05 — `pytest -q` 341 passed; `mypy src` OK; `ruff` clean; `git diff docs/` empty.
- **Overall:** pass
