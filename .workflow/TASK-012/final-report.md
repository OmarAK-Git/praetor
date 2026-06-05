# Final Report: TASK-012

## Status

**Complete** — walking skeleton decision flow, startup recovery, Phase 1 gate intake path.

## Deliverables

| Area | Files |
|------|-------|
| Engine package | `src/praetor/engine/{ids,skeleton,citations,edict,recovery,orchestrator}.py` |
| State hook | `open_state_store` → `run_engine_startup_recovery` |
| Attempts API | `fetch_all_non_terminal_attempts` in `state/attempts.py` |
| Tests | `tests/engine/test_walking_skeleton.py` (5), `test_crash_recovery.py` (18), `test_engine_ids.py` (2) |
| Scope guard | `engine` package allowed |

## Verification (2026-06-05, re-run after review hardening)

```
pytest -q tests/engine/                    → 25 passed
pytest -q                                  → 341 passed
mypy src                                   → OK (66 files)
ruff check src/praetor/engine tests/engine → All checks passed
git diff --name-only docs/                 → (empty)
```

## Behavior summary

- Hardcoded bundle/judgment intake → `DecisionEdict` + `NeverContainSnapshotRecord` on ledger, stamp payload on edict.
- Fault paths: `correlation_failure` (EMPTY_BUNDLE, abort), `config_over_budget` (no provider call), `invalid_model_citation`.
- Startup recovery: non-terminal attempts reconciled; stamp-resolved/ready-to-append get safe edict; never-contain directive scan + ledger revocation append + `never_contain_conflict` health alert; no `auto_contain` on recovery.

## Review follow-ups resolved (2026-06-05)

- **#1 EMPTY_BUNDLE single site:** `resolved_evidence_bundle_hash` is now the only substitution site; `build_decision_edict` resolves once and feeds both `decision_id` and the stored field (DEC-006). Pinned by `test_engine_ids.py`.
- **#3 crash window:** `test_crash_window_edict_appended_attempt_not_completed_does_not_duplicate` exercises the `ledger_has_edict_for_decision_id` True branch.
- **#4 unresolvable stamp:** `test_unresolvable_unknown_stamp_aborts_attempt_without_edict` covers `_ensure_terminal_stamp` → None → abort.
- **#5 failed stamp + auto_contain:** `test_failed_stamp_with_autocontain_candidate_downgrades_to_escalate` pins the downgrade (DEC-009).
- **#6 correlation-failure redelivery:** `test_correlation_failure_redelivery_produces_second_edict` pins the duplicate-edict behavior (DEC-010).
- **#7 docstring:** `run_engine_startup_recovery` now documents "steps 4, 5, 7"; store hook comment corrected (DEC-007).
- **Health-alert list:** `emitted_health_alert_ids` returns only this scan's conflict alerts (DEC-008).

## Known gaps (by design)

- PolicyGate / FakeProvider: Tasks 13–16
- Ledger append on all revocation write paths (activation/emergency): partial — startup scan only in Task 12
- Startup step 6 (idempotency/rate/breaker reconciliation): not implemented; no-op for v1 skeleton, owned by PolicyGate/breaker tasks
- Outcome-Matrix coupling enforced in tests, not a `DecisionEdict` model_validator (eval-harness Task 26)

## safe_to_commit

**yes** — verification ledger re-run and refreshed to match the tree (341 / engine 25).
