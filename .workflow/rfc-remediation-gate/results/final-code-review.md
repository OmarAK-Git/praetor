# Final Code Review — Reverse-Spec RFC Remediation Gate

**Review model:** cursor-grok-4.5-high  
**Reviewer role:** fresh `code-reviewer` (broad gate review)  
**Range reviewed:** `5220896bc8ae1ffd2b3315ceeece2d1c62e60cd4..HEAD` (`1f541fb^..21aa533`)  
**HEAD:** `21aa533e3081d180b16f55c979c84b722b29da6f`  
**Plan SoT:** `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md`  
**Gate plan:** `.workflow/rfc-remediation-gate/plan.md`  
**Working-tree noise:** ignored (untracked `AS_BUILT.md` / `DEBT_LEDGER.md` / `*_output.txt`, dirty memory-bank + autopilot queue are out of scope)

## Commits in range (7)

| SHA | Subject |
|---|---|
| `1f541fb` | config: log skipped malformed never-contain entries instead of silently dropping them |
| `7d88702` | correlation: add distinct metric for unsupported-EventID schema mismatches |
| `49df14b` | test: cover Security unsupported-EventID correlation metric branch |
| `38aded9` | test: add direct unit coverage for the engine.citations adapter |
| `ad2ebf7` | annotations: log malformed ledger edicts skipped during precedent fetch |
| `03f62cb` | revocation: add operator size-warning health alert for the unrotated feed file |
| `21aa533` | docs: record verified disposition of the reverse-spec RFC review |

`49df14b` is the Task-2 review-fix commit (test-only). Extra relative to the source plan’s six commit messages; in-scope and load-bearing for AC2 Security-branch coverage.

## Diff footprint (committed only)

16 files, +518/−2. Touched surfaces map 1:1 to the six plan tasks (+ AG-0095 scope-guard allowlist for Task 6 + Security metric test for Task 2):

- Task 1: `src/praetor/config/live.py`, `tests/config/test_live_never_contain_matching.py`
- Task 2: metrics + correlation + orchestrator wiring + metrics/correlation tests (+ `49df14b`)
- Task 3: `tests/engine/test_citations.py` only
- Task 4: `src/praetor/annotations/precedent.py`, `tests/annotations/test_precedent.py`
- Task 5: `src/praetor/config/constants.py`, `src/praetor/revocation/exporter.py`, `tests/revocation/test_feed_exporter.py`
- Task 6: `docs/proposals/reverse_spec_rfc_disposition.md`, `tests/contracts/test_scope_guard.py`

No policy-gate, stamp, tickets, Outcome Matrix enum, feed format/sequence/checksum, or citations production-module edits in the range.

---

## 1. Spec compliance (six tasks + mandated exclusions)

| Task | Plan intent | Result |
|---|---|---|
| 1 — never-contain skip logging (RFC-003 rescoped) | Warning on both `PreflightError` arms; match/skip semantics unchanged | **Met** — `_logger.warning(...)` then same `return False` / `continue` |
| 2 — unsupported-EventID metric (RFC-004) | Snapshot field + collector + correlator opt-in metric + intake wiring | **Met** — Sysmon + Security loops record; orchestrator threads `metrics_collector`; `49df14b` closes Security AC gap |
| 3 — citations adapter test (RFC-006 rescoped) | Direct adapter tests; no production change | **Met** — three bool cases via `engine.citations`; `src/` untouched |
| 4 — precedent malformed-edict log (RFC-005 rescoped) | Log on `ValidationError` skip; no ranking/auth change | **Met** — warning then `return None`; public APIs unchanged |
| 5 — feed size warning (RFC-002 rescoped) | Observational health alert; no rotation | **Met** — `check_feed_file_size_warning` + startup wiring; feed file not mutated; actuation helpers untouched |
| 6 — disposition record | Six RFC verdicts; RFC-001 rejected; rotation out of scope | **Met** — disposition doc matches plan template; AG-0095 exact-path allowlist added |

### Mandated exclusions (verified against diff, not assumed)

| Exclusion | Evidence |
|---|---|
| **RFC-001 rejected** — no stamp/ledger order invert | No files under `policy/`, `tickets/`, stamp paths; disposition records Rejected under DEC-053 |
| **RFC-002 rotation excluded** | Exporter size path only `exists`/`stat` + health-alert outbox write; no truncate/rotate/segment; comments pin “no rotation machinery”; disposition says rotation stays out of scope |
| Never-contain matching semantics unchanged | Diff only wraps existing except arms with logging |
| Disposition / authorization outcomes unchanged | No `evaluate_policy_gate` edits; orchestrator gate call site untouched by this range |

---

## 2. Global no-change constraints (diff-verified)

| Constraint | Verdict | How verified |
|---|---|---|
| No change to `evaluate_policy_gate` authorization outcomes or disposition semantics | **Hold** | Zero diffs in policy/gate modules; Task 1/4 only add logs on skip paths that already skipped; Task 2/5 observability only |
| No change to stamp-before-`critical_transaction` ordering (DEC-053) | **Hold** | No stamp/tickets product diffs; Task 6 text keeps RFC-001 Rejected |
| No new `OutcomeMatrixFaultFlag` enum member | **Hold** | Diff contains no `OutcomeMatrixFaultFlag` definition/member additions |
| No revocation-feed rotation, truncation, segmentation, format, sequence, checksum, or actuation-state change | **Hold** | Size helper does not touch sink/append/validate/sequence/checksum/`set_feed_unhealthy`/`is_feed_actuation_blocked` bodies; alert_code is distinct from `revocation_feed_unhealthy` |
| No locking added to single-writer `MetricsCollector` | **Hold** | New counter is simple `+= 1` like peers; no `Lock`/`threading` in metrics diff |

**Production path for Task 5 default:** `open_state_store` → `run_feed_startup_hook_for_db(...)` without override → lazy resolve to `DEFAULT_FEED_FILE_SIZE_WARNING_BYTES` (500_000_000). Lazy import (vs plan top-level) is the justified circular-import adaptation; behavior matches plan intent.

---

## 3. Cross-task interactions / regression risk

Reviewed for interactions per-task reviews could miss:

1. **MetricsSnapshot required field** — `correlation_unsupported_event_id_total` has no default; sole construction site is `MetricsCollector.snapshot()` and it includes the field. No incomplete-constructor hole across tasks.
2. **Health-alert outbox sharing (Task 5 vs existing unhealthy path)** — same `write_pending_health_alert` / `SystemHealthAlert(alert_code, emitted_at)` shape; distinct `alert_code`; does not flip feed-unhealthy or actuation-block flags.
3. **Orchestrator intake** — Task 2 only adds defaulted metric threading into `_resolve_intake_evidence_bundle` / `correlate_telemetry`. Empty-facts → `correlation_failed` path unchanged; metric records before that return so schema-mismatch empty bundles are distinguishable.
4. **Logging tasks (1 + 4)** — independent modules; neither alters PolicyGate, precedent ranking, or never-contain validation on the write path.
5. **Task 3 + citations call site** — adapter production code unchanged; orchestrator still calls `validate_skeleton_citations` as before.
6. **Scope-guard (Task 6)** — exact path allowlist only; no `docs/proposals/**` broadening.

No cross-task Critical/Important regressions found.

---

## 4. Test quality (would revert fail?)

| Area | Would fail if production behavior reverted? | Notes |
|---|---|---|
| Task 1 never-contain logs | **Yes** — malformed cases assert warning substring; empty `caplog` without `_logger.warning` | Also asserts skip-and-continue still matches valid entry |
| Task 2 collector counter | **Yes** — snapshot field == 2 after two records | |
| Task 2 Sysmon unsupported metric | **Yes** — asserts `correlation_unsupported_event_id_total == 1` with mixed events | |
| Task 2 Security unsupported metric (`49df14b`) | **Yes** — deleting Security `record_*` arm fails new test | Closes prior Important gap |
| Task 2 no-collector path | **Yes** for crash; does not assert metric | Compatibility only |
| Task 2 orchestrator wiring | **Weak** — no assertion that intake passes collector into correlate | Wiring verified by inspection; engine suite is non-pinning for this kwarg (Minor) |
| Task 3 citations adapter | **Yes** for always-True / always-False stubs | Imports adapter, not evidence module directly |
| Task 4 precedent log | **Yes** — asserts warning text + decision_id; empty precedents | Corrupt JSON hits ValidationError path, not missing-row |
| Task 5 size warning helper | **Yes** — above-threshold outbox row; below-threshold absence | |
| Task 5 startup wiring | **Yes** — `run_feed_startup_hook_for_db` with low threshold asserts alert | Exercises post-reconcile path via whitespace-filled file |
| Task 6 disposition + scope-guard | **Yes** for dirty unsanctioned docs path | Allowlist entry is load-bearing for AG-0095 |

Fixture adaptation in Task 2 (flat `@timestamp` / `record_id` vs plan’s nested `System` shape) matches real correlator field access — correct, not a defect.

---

## 5. Scope audit

Everything in the committed range is inside plan intent:

- Extra Security metric test (`49df14b`): required to satisfy Task 2 AC for both event families after first review.
- Extra feed wiring test: packet/AC requirement beyond the two helper tests in the source plan.
- Scope-guard +1 path: necessary AG-0095 companion to the disposition doc (source plan omitted it; run plan correctly included it).

No drive-by refactors, no RFC-001 implementation, no rotation machinery, no Outcome Matrix expansion.

---

## Findings

### Critical (blocking)

None.

### Important (blocking)

None.

### Minor (non-blocking / track)

1. **`orchestrator.py` Task-2 wiring unasserted** — dropping `metrics=metrics_collector` from the `correlate_telemetry` call would not fail a dedicated test. Acceptable vs plan Step 10 (engine regression); optional follow-up to lock AC3.
2. **`exporter.py` reconcile-failure early return** — size warning skipped when reconcile fails (plan control flow). Large corrupt feeds rely on unhealthy signaling only.
3. **Feed size warning re-emit** — each above-threshold successful startup inserts a new outbox row (new UUID), same pattern as unhealthy alerts; no dedupe.
4. **`test_run_feed_startup_hook_emits_size_warning_when_threshold_exceeded`** — name implies hook coverage; body tests the helper only (wiring covered by the third test).
5. **Log-level assertions** — Tasks 1/4 assert message substrings, not `WARNING` level (plan-literal).

---

## Per-task artifact completeness (gate acceptance #1)

All six `.workflow/rfc-remediation-0{1-6}-*/results/` trees contain implementer, code-review, and verifier artifacts. Task 2 re-review after `49df14b` is PASS. This document is the broad final review artifact.

---

## Overall verdict

**PASS**

No Critical or Important findings. The seven-commit range implements the six approved remediation tasks, preserves all global no-change constraints (including RFC-001 rejection and no feed rotation), keeps tests meaningful against revert, and stays inside plan scope (plus justified AG-0095 / Security-branch companions).
