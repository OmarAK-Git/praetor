# Review

## Open questions

None blocking implementation.

## Gaps vs docs

- `RateLimitPolicy` lists scopes only; numeric per-scope ceilings use DEC-029 (limit=1/scope/window).
- `per_asset_group` collapses to host `asset_id` until multi-host groups ship (DEC-030).
- Containment breaker recovery is window-elapse on open-check; successes apply when closed (DEC-031).
- Gate entry initializes health emit schema (`init_health_alert_emit_schema`) for breaker trips.

## Deferred

- Engine PolicyGate wiring (DEC-028 single emit transaction).

---

## Gatekeeper Review (post-implementation)

**Verdict: CHANGES REQUESTED.** Suite is green (31 policy tests pass) and the
artifacts are internally consistent, but green is masking the two requirements this
task exists for. REQ-003 (race-safety) and breaker recovery are validated by proxy
tests that never exercise the real behavior, and the race path is broken on the
branch no test reaches. `final-report.md` safe_to_commit is overridden to **no**.

### Adequately covered (do not re-litigate)
- `per_host`, `per_subnet` (two distinct hosts) limits; REQ-002 unregistered→`per_host`
  only; rate-limit sliding-window reset; breaker trips at threshold (REQ-004); single
  health alert on trip (REQ-005); counters-unchanged-while-open (REQ-006); success
  *tally* reset while closed (REQ-007 as literally written).
- Outcome-matrix wiring matches spec 62-64 / contracts 448-450: `rate_limit_exceeded`
  → escalate/false, `containment_breaker_open` → escalate/false,
  `provider_health_breaker_open` → escalate/true. System-fault asymmetry is correct.

### Blockers
1. **Containment breaker never closes** — contradicts spec line 185 ("…alerts, and
   recovery"). Once `is_open=1`, every auto_contain short-circuits at `gate.py:224`
   (`is_containment_breaker_open` is a plain SELECT). `_advance_breaker_window`'s
   window-elapse reset is never reached while open; `record_containment_success_*`
   returns False when open and only runs post-emit; `reconcile_policy_state` never
   resets `is_open`. Grep confirms no path clears it. No test asserts recovery —
   `test_success_reset_threshold_clears_failure_state` only resets the failure *count*
   while closed.
2. **Race-loser path rolls back its own failure/trip/alert** — `gate.py:287-302`.
   Raising `_PolicyGateRollback` inside `critical_transaction` triggers ROLLBACK
   (`sqlite_guard.py:115-117`), discarding the failure increment, breaker trip, and
   enqueued alert from line 294; `gate.py:337` then flushes a rolled-back batch_id.
   This is the exact mechanism REQ-003 defends, and it's broken. Contrast the
   committed pre-check helper `_record_rate_limit_failure` (gate.py:111-123).

### Coverage corrections (traceability.md is optimistic)
- REQ-003 row: `test_concurrent_attempts_serialized_no_double_emit` is **sequential**;
  the second call escalates via the pre-check (`gate.py:257`), so the in-tx re-check
  branch (287-302) is dead under the suite. Serialization is unverified.
- REQ-001 (`per_asset_group`) row: `rate_limit._asset_groups_for_registered_host`
  only returns the host's own `asset_id`, so `per_asset_group == per_host`. The test
  `test_per_asset_group_limit_blocks_second_host_in_same_group` uses the **same host
  twice** and passes via `per_host`. Two distinct hosts in one group are untested and
  would not block. (Mitigant: spec line 440 defers asset-group containment.)

### Medium
- Gate enqueues breaker alerts but only calls `init_policy_state_schema`, never
  `init_health_alert_outbox_schema`. A trip with the outbox table absent raises
  uncaught out of `evaluate_policy_gate`. Both breaker tests hide this by seeding the
  outbox by hand.

### Fix prompt (hand to Cursor — edits source, not this slug)

```
TASK-018 follow-up. Policy modules are committed and the suite is green, but a
gatekeeper review found the two requirements this task exists for (REQ-003
race-safety, REQ-007/breaker recovery) are validated by proxy tests that don't
exercise the real behavior, and one path is broken. Do NOT touch docs/spec.md
(frozen this phase). Record any behavioral decision in memory-bank/decisions.md.
Run full pytest + mypy src + ruff check src tests when done.

1. CONTAINMENT BREAKER NEVER RECOVERS (contradicts spec line 185 "...alerts, and
   recovery"). Once circuit_breaker_state.is_open=1 for 'containment', nothing clears
   it: gate.py:224 is_containment_breaker_open() is a plain SELECT,
   record_containment_success_in_transaction() returns False when open and only runs
   post-emit, reconcile_policy_state() never resets is_open.
   (a) Implement window-based recovery — the open-check must advance the breaker
       window so an elapsed window_seconds closes the breaker (reset logic already
       exists in circuit_breaker._advance_breaker_window; it's just never reached on
       the open path). Successes can't recover it because auto_contain is blocked
       while open, so window-elapse is the only viable mechanism — do not wire
       successes.
   (b) Add a test: trip the breaker, advance `now` past window_seconds, assert the
       next auto_contain is ALLOWED; assert still blocked at now+window_seconds-1.
   (c) If v1 instead has NO auto-recovery (manual SOC reset), record that decision in
       decisions.md AND add a test asserting it stays open past window_seconds plus a
       documented reset entry point. Silent permanent-open is not acceptable.

2. RACE-LOSER PATH BROKEN (gate.py:287-302). Raising _PolicyGateRollback inside
   `with critical_transaction(conn)` triggers ROLLBACK (sqlite_guard.py:115-117),
   discarding the failure increment, breaker trip, AND the alert from line 294; line
   337 then flushes a rolled-back batch_id. Record the in-transaction race-loss
   failure in a SEPARATE committed transaction (mirror _record_rate_limit_failure at
   gate.py:111-123) so the failure count, any trip, and the alert survive the rollback
   of the emit attempt; then flush. Verify no double-count vs the pre-check path.

3. PROVE SERIALIZATION (REQ-003). Add a test that creates the real race: drive two
   separate guarded connections so a second emit commits between the first gate's
   pre-check (gate.py:257) and its in-tx re-check (gate.py:287); assert (a) exactly
   one directive emitted, (b) loser escalates rate_limit_exceeded, (c) failure
   recorded exactly once. This branch is currently dead under the suite.

4. per_asset_group is degenerate (rate_limit._asset_groups_for_registered_host returns
   only the host's own asset_id, so per_asset_group == per_host). Either make the test
   honest (rename + assert intentional collapse to per_host, cite spec line 440
   deferral in a decisions.md note, fix the REQ-001 traceability row) or implement real
   group membership. Don't leave a test named "blocks_second_host_in_same_group" that
   uses one host twice.

5. Outbox-schema dependency: a breaker trip inside evaluate_policy_gate enqueues a
   health alert, but the gate only calls init_policy_state_schema, not
   init_health_alert_outbox_schema. Add an integration test driving the gate to a trip
   WITHOUT pre-initializing the outbox; confirm no raise (guarantee the schema at gate
   entry or document+pin the startup contract).

Acceptance: new tests for (1b), (3), (5) and corrected (4) pass; full pytest + mypy +
ruff clean. Update verification.md / traceability.md to reflect genuine coverage.
```

---

## Gatekeeper Re-review (follow-up verified)

**Verdict: ACCEPTED.** Both blockers resolved with real tests, not proxies.
437 passed (was 434), mypy clean, ruff clean.

| # | Fix | Verifying test |
|---|---|---|
| 1 breaker recovery | `is_containment_breaker_open(conn, policy=, now=)` advances the window; gate passes `policy`+`now` (gate.py:228-232); DEC-031 | `test_breaker_recovers_after_window_elapses` — blocked at +59s, recovered at +60s |
| 2 race-loser | distinct `_RateLimitRaceLoss` caught outside the rolled-back tx; failure recorded via separate committed `_record_rate_limit_failure` (gate.py:338-341) | `test_in_tx_rate_limit_race_loser_records_single_failure` — failure_count==1 survives rollback |
| 3 serialization | `_test_before_emit_transaction` seam drives a second real connection to commit in the pre-check↔emit-tx window | same test — exactly 1 directive, loser escalates, 1 failure; in-tx branch now live |
| 4 per_asset_group | honest collapse test + DEC-030 | `test_per_asset_group_scope_collapses_to_per_host_for_v1` |
| 5 outbox schema | gate calls `init_health_alert_emit_schema` (gate.py:173) | `test_gate_breaker_trip_without_preinitialized_outbox` — drops tables, drives trip |

No double-count: `test_pre_check_rate_limit_failure_not_double_counted` pins the
sequential path at failure_count==1.

**Minor (non-blocking):** `evaluate_policy_gate` carries a `_test_before_emit_transaction`
hook in its production signature (keyword-only, underscore-prefixed, defaults None).
Pragmatic seam for deterministic race testing; acceptable.
