# Phase 1 Gate — Consolidated Punch-List

**Date:** 2026-06-05
**Scope:** Tasks 1–12 (durable walking skeleton)
**Sources merged:** Claude review (test/lint hygiene + safety-invariant audit) + IDE review (runtime-integration audit)
**Gate decision:** **CLEARED 2026-06-05** — B1 + B2 fixed and independently re-verified (343 passed, mypy clean, `ruff check src tests` clean; ledger appends confirmed inside `critical_transaction`; chain-membership regressions added). T1/T2 logged as Tasks 17–19 / Task 13 prerequisites. Sprint numbering reconciled. Residual watch item: when a production entrypoint lands, it must pass a held `SingletonLock` to `open_state_store` and a test must reject the lockless path (carry into Tasks 17–19 prerequisites). D1 intentionally unchanged.

> Original HOLD decision and findings retained below for audit history.

---

## Verification actually run (not self-reported)

### Closure verification (2026-06-08)

| Check | Command | Result |
|---|---|---|
| Test suite | `python -m pytest -q` | **343 passed** |
| Types | `python -m mypy src` | **clean, 66 files** |
| Lint | `python -m ruff check src tests` | **clean** |

### Original HOLD verification (2026-06-05)

| Check | Command | Result |
|---|---|---|
| Test suite | `python -m pytest -q` | **341 passed**, 0 failed, 0 runtime skips (1 conditional skip fires only when git absent) |
| Types | `python -m mypy src` | **clean, 66 files** |
| Lint | `python -m ruff check src tests` | **54 violations** (see L1) — repo-wide ruff was never green; per-task "ruff OK" was scoped to changed files. (An earlier `src`-only run reported 32; the gate command includes `tests` and the config selects `UP` rules.) |
| Crash safety | `pytest tests/engine/test_crash_recovery.py` | 18 passed; `never_autocontains[5 states]` genuinely asserts `final_disposition != AUTO_CONTAIN` |

The IDE could not get fresh exit status for pytest/mypy/ruff and relied on TASK-012's self-reported "341 passed / mypy OK / ruff clean." The first two reproduce; **"ruff clean" is false** (L1).

---

## BLOCKER — must fix or document an explicit deferral before Phase 2

### B1. Live emergency & activation revocations are not appended to the hash-chained ledger
**Severity:** Critical · **Source:** IDE · **Status:** confirmed by code read AND runtime probe

**Direct spec violation (not just a done-when):**
- `docs/spec.md:248` — emergency entries: "Each entry **is written to the ledger immediately**…"
- `docs/spec.md:220` — "The feed is a delivery projection of `DirectiveRevocationRecord`s **already committed to the hash-chained ledger**." Writing a feed row without a ledger append means the feed projects records that are not in the system of record.
- `docs/spec.md:257,301` — `DirectiveRevocationRecord` is a ledger record type interleaved in the chain.

**Runtime probe (IDE):** `emergency add → ledger_types: []` · `activation reconciliation → revocation_rows: 1, feed_rows: 1, ledger_types: []` · `startup scan → ledger_types: ['directive_revocation']`. Startup recovery is wired; the live emergency/activation surfaces are not.

- `append_ledger_record` is called in only two sites: `src/praetor/engine/edict.py:133-134` (edicts + snapshots) and `src/praetor/engine/recovery.py:313` (startup reconciliation).
- The live emergency surface writes revocations via `src/praetor/config/emergency.py:150` (`write_automated_revocation_in_transaction`) + `mark_directive_revoked` — **no `append_ledger_record`**.
- `src/praetor/state/store.py:192` (`_write_revocation_in_transaction`) writes the `directive_revocation_records` table + `revocation_feed_outbox` only — **not** the chain.
- `src/praetor/config/state.py:284` (`insert_emergency_record`) writes the `emergency_never_contain_records` table only — the `EmergencyNeverContainRecord` is **never** chained at runtime.
- **Proof of intent (the asymmetry):** the *identical* never-contain-conflict revocation appends to the ledger at startup (`recovery.py:312-313` does both the SQLite write and `append_ledger_record`) but the live path omits it. Same operation, two code paths, only one chains.

**Why it's a blocker:** Task 10 done-when ("all four record types share one tamper-evident chain") and the "chain as revocation system of record" property are met only in isolated hash-chain unit tests, not at runtime. The chain in production would contain edicts + snapshots + startup-reconciled revocations, but **not** live revocations or any emergency entry.

**Test blind spot:** `tests/config/test_emergency_never_contain.py` and `tests/config/test_config_activation.py` assert only SQLite revocation/outbox rows, so the ledger omission passes green.

**Disposition: FIX — not deferrable.** Deferring to Task 20 was considered and rejected: `docs/spec.md:220,248` make live emergency/activation ledger appends a Phase 1 spec requirement, and the running system is in violation today (feed rows project uncommitted revocations; emergency entries not written immediately). The fix:
1. Wire `append_ledger_record` into `emergency.py` and the activation reconciliation path, using the same in-transaction pattern as `recovery.py:312-313`, so the ledger append and the revocation/feed-row write commit atomically.
2. Append the `EmergencyNeverContainRecord` itself to the chain (spec:248 "written to the ledger immediately") — Task 20 does not cover this, so it must land regardless.
3. Add tests asserting **chain membership** for live emergency revocations, activation revocations, and the emergency record (closes the blind spot below).

---

### B2. Singleton/WAL startup guard is not invoked on the integrated open path
**Severity:** Important (elevated to blocker-class: it's a core safety guard relying on convention) · **Source:** IDE · **Status:** confirmed

- `src/praetor/state/store.py:304` (`open_state_store`) — the path the engine and recovery actually use — explicitly "does not acquire the Task 5 singleton lock; production callers must hold `SingletonLock`," and never calls `run_startup_sqlite_guard`.
- `run_startup_sqlite_guard` (`src/praetor/state/sqlite_guard.py:122`) is the only code that enforces `singleton.is_held`; it is exercised only in isolation + the subprocess test.
- `open_state_store` calls `init_state_dir` (one-shot WAL bootstrap) *before* `create_guarded_connection`, so a non-WAL DB is silently re-flipped to WAL instead of exiting non-zero.

**Why it matters:** Task 5 done-when ("WAL misconfiguration exits non-zero"; "a second process cannot start") is satisfied only by the isolated guard path, not the integrated entry point. The production binary's safety depends on an undocumented caller convention.

**Disposition:** Either route the production startup through `run_startup_sqlite_guard` (or have `open_state_store` accept/verify a held `SingletonLock` and verify-rather-than-bootstrap WAL), or document the operator responsibility boundary explicitly and add an assertion that fails closed when the lock is not held.

---

## TRACK — real, lower-risk; fix during early Phase 2

### T1. Startup recovery step 6 (idempotency-key / rate-counter / breaker reconciliation) is absent
**Severity:** Important · **Source:** IDE + code · **Status:** self-documented at `src/praetor/engine/recovery.py:334`

Low immediate risk under the no-containment skeleton (no rate/breaker state mutated yet), but it is a spec startup invariant. Must land before Phase 2 policy work (Tasks 17–19) introduces the state it is meant to reconcile. Track as an explicit Phase 2 prerequisite.

### T2. `pending_stamp` recovery with no existing stamp-outbox row is not directly pinned
**Severity:** Minor · **Source:** IDE (orchestrator) · **Status:** coverage gap

Crash at `pending_stamp` before any stamp-outbox row exists is not directly tested. Stays non-containment-safe for the hardcoded skeleton, but add a regression test before provider work (Task 13) so the path is pinned once real stamps exist.

### L1. Repo-wide ruff was never green
**Severity:** Low (cosmetic, but the lint gate wasn't actually a gate) · **Source:** Claude + IDE · **Status:** confirmed, **54 violations** via `ruff check src tests`

```
36 E501   line too long
 5 I001   import order
 5 UP042   (enum upgrade)
 4 F401   unused imports (containment.py, evidence.py, identity.py)
 3 UP017   datetime.timezone.utc → datetime.UTC
 1 F811   duplicate `SchemaVersionV1` import — src/praetor/contracts/__init__.py:3
```
The F811 is a same-line duplicate import (typo), not a logic bug. Many are auto-fixable (`ruff check --fix`); E501 needs manual wrapping. The earlier 32-count was a `src`-only run; the gate command is `ruff check src tests` and the `pyproject.toml` config selects `UP` rules. "ruff OK" in task verifications was scoped to changed files, not global.

---

## DESIGN NOTE — disagree it's a blocker

### D1. Correlation-failure redelivery produces a second EMPTY_BUNDLE edict
**IDE severity:** Critical · **My assessment:** intentional & contract-consistent — downgrade to design note

- Mechanism confirmed: `src/praetor/engine/orchestrator.py:226-231` (`_finish_correlation_failure`) calls `append_edict_and_snapshot` + `abort_attempt`, deliberately **not** `persist_edict_and_complete_attempt`, so no completed-decision row is written and redelivery re-runs.
- The "one completed edict per alert/bundle/config tuple" invariant governs the completed-decisions dedup table. Correlation-failure escalations bypass it **on purpose**: the bundle could not be assembled (`EMPTY_BUNDLE` sentinel, not a real bundle), so redelivery should re-attempt once telemetry recovers — consistent with Task 6 ("aborted attempts do not block future changed-input attempts"). Permanently deduping a transient system fault to a stale escalate would be the actual bug.
- Carries `system_fault_escalation=true`; the second-edict behavior is pinned by `tests/engine/test_crash_recovery.py::test_correlation_failure_redelivery_produces_second_edict` — a deliberate decision.

**Legitimate residual:** audit-log amplification — N redeliveries during a correlation outage produce N escalate edicts. Worth a one-line note in the operator runbook (Task 35); not a safety failure, not a gate blocker.

---

## What each review got right / missed

| | Claude review | IDE review |
|---|---|---|
| Strength | Ran everything; caught lint debt (L1); confirmed crash-safety invariant is real | Static code read; caught runtime-integration gaps (B1, B2) the green suite masks |
| Miss | Under-weighted integration wiring (B1, B2) | Ran nothing; repeated false "ruff clean"; overstated D1 as Critical |

Neither review alone was sufficient. The green suite hides B1/B2 because the tests assert SQLite rows and exercise guards in isolation rather than asserting chain membership / lock enforcement on the integrated path.

---

## Exit criteria to clear the gate
1. **B1 fixed** (not deferrable per spec:220,248): live emergency + activation revocations and the `EmergencyNeverContainRecord` all appended to the chain in-transaction.
2. **B2** fixed, or operator responsibility boundary documented **and** a fail-closed assertion added.
3. New tests asserting **ledger chain membership** for live emergency revocations, activation revocations, and emergency records (closes the blind spot that hid B1 from a 341-green suite).
4. **T1** logged as a hard prerequisite for Tasks 17–19; **T2** regression added or logged for Task 13.
5. Repo-wide ruff (`ruff check src tests`) cleared, or explicitly gated/configured with the residual stated — no "ruff clean" claims while 54 errors stand.
6. Sprint numbering reconciled in `docs/plan.md` (Sprint 1 = Tasks 1–11 vs Phase 1 gate = Tasks 1–12).
7. Fresh, pasted output for `pytest -q`, `mypy src`, `ruff check src tests`.
