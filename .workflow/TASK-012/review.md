# Review: TASK-012

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Single `critical_transaction` for ledger append + attempt completion | Avoids nested-transaction guard (DEC-018) |
| DEC-002 | In-transaction FSM helpers in `engine/edict.py` | Recovery and intake share finalize path without nested `transition_attempt` |
| DEC-003 | `run_engine_startup_recovery` in `open_state_store` before feed hook | Spec startup steps 4,5,7 run before feed recovery (step 8) |
| DEC-004 | Skeleton policy never emits `auto_contain` | Phase 1 gate: no recovery path emits containment |
| DEC-005 | Ledger append on startup never-contain revocations only | Activation-time revocations (Task 9) still omit ledger append — out of Task 12 file list |

## Review-driven decisions (2026-06-05)

| ID | Decision | Rationale |
|---|---|---|
| DEC-006 | Single EMPTY_BUNDLE substitution site `resolved_evidence_bundle_hash` | §3.3 forbids re-deriving; `build_decision_edict` now resolves once and feeds both `decision_id` and the stored `evidence_bundle_hash`. Pinned by `test_stored_bundle_hash_equals_decision_id_input` |
| DEC-007 | `run_engine_startup_recovery` docstring corrected to "steps 4, 5, 7" (not 4–7) | Step 6 (idempotency/rate/breaker reconciliation) is intentionally absent for the v1 skeleton; do not let the next task assume it is covered |
| DEC-008 | `never_contain_conflict` health alerts emitted on startup directive scan | Spec step 7 requires conflict alerts before intake; reuses `config.health_emit` batch pattern. Returned `emitted_health_alert_ids` contains only this scan's conflict alerts (prior unflushed alerts are drained as a side effect, not returned) |
| DEC-009 | `ticket_stamp_failed` with `auto_contain` candidate downgrades to `escalate` | Recovery never emits containment; the override keeps `ticket_stamp_failed` / `system_fault=false` / `proposed=auto_contain`. Pinned by `test_failed_stamp_with_autocontain_candidate_downgrades_to_escalate` |
| DEC-010 | Correlation-failure redelivery may produce a second EMPTY_BUNDLE escalate edict | The abort path writes no completed-decision three-tuple row, so a redelivered alert re-allocates (correlation may succeed later). Pinned by `test_correlation_failure_redelivery_produces_second_edict` |

## Gaps (docs / follow-up)

| Gap | Notes |
|---|---|
| Activation/emergency revocation ledger append | Task 9 paths write feed + SQLite revocation rows; ledger append only in engine startup directive scan and recovery edict path |
| Real correlator / PolicyGate / provider | Tasks 13–17 |
| Startup step 6 (idempotency/rate/breaker reconciliation) | Not implemented; no-op for v1 skeleton (no containment emitted). Owned by PolicyGate/breaker tasks. Documented in `run_engine_startup_recovery` docstring |
| Outcome-Matrix coupling enforced only in tests | `assert_outcome_matrix_edict` checks fault_flag↔system_fault pairing per row; no `DecisionEdict` model_validator yet — eval-harness task (26) owns the global invariant |
| Engine-appended `verify_ledger_chain` | Chain continuity rests on `append_ledger_record` (verified in Task 10); engine tests assert the snapshot↔edict audit link only |
| `docs/` unchanged | Per command hard limit |

## safe_to_commit

**yes** — re-run 2026-06-05: `pytest -q` 341 passed, engine 25; `mypy src` OK; `ruff` clean; `git diff docs/` empty.
