# Phase 2 Gate — Consolidated Punch-List

**Date:** 2026-06-15
**Scope:** Tasks 13–27 (judgment & policy discipline)
**Sources merged:** Claude review (full-suite verification + integration/coverage audit against known failure modes) + IDE review (independent gate-wide verification + execution of remediation)
**Gate decision:** **CLEARED AS PASS-WITH-CONDITIONS 2026-06-15** — all Phase 2 components are complete and independently verified (629 passed, 1 deselected, 3 xfailed; mypy strict clean 104 files; ruff clean; evals 24/24 exit 0). The one material finding — **PolicyGate and metrics are implemented and tested but not on the production decision path** (F1) — is **fail-safe** (the orchestrator hard-downgrades `auto_contain → escalate`, so nothing ungated can contain) and is **formally deferred to Task 28a (Phase 3) per DEC-048**, tracked with three strict-xfail tripwire tests that fail the suite if the wiring lands without removing them. Governance gaps (untracked follow-ups, unratified DEC-028, README drift, sprint-grouping inconsistency) are closed. Residual TRACK items (T1, T2) carried into Task 28a.

> Unlike the Phase 1 gate (B1 was an active `spec.md` violation, not deferrable), the Phase 2 central finding is a completeness/coverage gap on a fail-safe path. That is what makes a conditional pass defensible here rather than a HOLD.

---

## Verification actually run (not self-reported)

### Claude verification (2026-06-15)

| Check | Command | Result |
|---|---|---|
| Test suite | `python -m pytest -q` | **629 passed, 1 deselected** |
| Types | `python -m mypy` | **clean, 104 source files** |
| Lint | `python -m ruff check` | **clean** |
| Phase 2 evals | `python -m evals.harness` | **24/24 PASS, exit 0** |

### IDE closure verification (2026-06-15, post-remediation)

| Check | Command | Result |
|---|---|---|
| Test suite | `python -m pytest -q -rs` | **629 passed, 1 deselected, 3 xfailed** (tripwires XFAIL — not XPASS, not FAIL) |
| Types | `python -m mypy` | **clean, 104 source files** |
| Lint | `python -m ruff check` | **clean** |
| Phase 2 evals | `python -m evals.harness` | **24/24 PASS, exit 0** |
| Scope | — | confirmed **no `src/` file and no `docs/spec.md`** modified |

The green mechanical suite is necessary but not sufficient: it does **not** exercise containment safety through the production orchestrator (see F1 / the harness blind spot).

---

## FINDING — central, fail-safe, deferred with tracking

### F1. PolicyGate and metrics are not on the production decision path
**Severity:** Important (architectural completeness) · **Source:** Claude (audit) + IDE (independent confirmation) · **Status:** CONFIRMED by code read AND scenario→runner mapping · **Disposition: DEFER to Task 28a + track (DEC-048)**

**The gap:**
- `src/praetor/engine/orchestrator.py:240-247` — `process_alert_intake` uses `skeleton_policy_result` and **unconditionally downgrades any `auto_contain` → `escalate`**. `skeleton_policy_result` (`src/praetor/engine/edict.py:38-47`) never authorizes containment.
- `evaluate_policy_gate` is called from **no production module** — only `src/praetor/policy/gate.py:157` (definition), the `policy/__init__.py` re-export, `evals/harness.py`, and tests.
- `MetricsCollector` is **never instantiated outside tests** — only `metrics/collector.py` (definition), `metrics/__init__.py` (export), and `tests/metrics/test_metrics.py`.
- Consequence: on the live intake path, the deterministic safety checks (never-contain snapshot/live, account identity corroboration, rate limits, containment/provider-health breakers, feed health, policy ambiguity, idempotency) **do not run**, and the system **cannot emit `auto_contain` end-to-end**. Recovery repeats the skeleton policy (`src/praetor/engine/recovery.py`).

**Harness blind spot (why the green suite masks it):** the harness has two runners — `engine_intake` → `process_alert_intake` (`evals/harness.py:416-458`) and `policy_gate` → `evaluate_policy_gate` directly (`evals/harness.py:606+`). **Every safety-critical scenario routes to `policy_gate`**, bypassing the orchestrator:

| Scenario | Runner |
|---|---|
| `confirmed_malicious_sequence` (the only `auto_contain` case) | `policy_gate` |
| `never_contain_target`, `incomplete_telemetry`, `policy_ambiguity` | `policy_gate` |
| `rate_limit_exceeded`, `containment_breaker_open`, `provider_health_breaker_open` | `policy_gate` |
| `account_containment_feature_gate_disabled`, `emergency_never_contain_blocks_inflight` | `policy_gate` |
| `revocation_feed_unhealthy_blocks_autocontain` | `revocation_feed_degraded_mode` |
| `engine_intake` only covers: `benign_admin_activity`, `config_over_budget`, `correlation_failure`, `invalid_model_citation`, `malformed_json`, `provider_refusal`, `provider_timeout`, `ticket_stamp_failed` | `engine_intake` |

No eval or test drives `auto_contain` or a never-contain/breaker block **through `process_alert_intake`**. Acknowledged at `.workflow/TASK-026/final-report.md`.

**Known-but-untracked at discovery:** the wiring was flagged as a follow-up in `.workflow/TASK-017/final-report.md:73` and the metrics gap in `.workflow/TASK-024/final-report.md:46`, but neither was a scheduled task in `docs/plan.md`, and `DEC-028` (the wiring acceptance criterion) lived only in `memory-bank/decisions.md:34`.

**Why DEFER and not FIX-now:** Sprint 3 / Task 28 rebuilds the orchestrator to consume correlated `EvidenceBundle`s (today it hardcodes `SKELETON_EVIDENCE_BUNDLE`). Wiring the gate into the walking-skeleton intake would be discarded immediately. The current state is fail-safe (no ungated containment is possible), so this is deferrable — provided it is tracked and cannot be silently shipped over.

**Resolution applied (verified by IDE):**
1. **DEC-028 ratified** into `docs/decisions.md` (gate = pure evaluator; engine = single serializable emit transaction).
2. **DEC-048 recorded** — deferral of PolicyGate + metrics integration to Task 28a, with the fail-safe rationale and the tripwire guard.
3. **Task 28a added to `docs/plan.md`** — "Production Orchestrator PolicyGate and Metrics Integration," `Depends on: Tasks 17-24, 26, 28`, `Blocks: Task 31 / Phase 3 gate`, positioned **after Task 28** (the Task 28 dependency is what structurally prevents wiring against the skeleton).
4. **Phase 2 gate** marked conditional pass; **Phase 3 gate** updated to require the wiring in one serializable emit transaction, end-to-end `engine_intake` evals (gated `auto_contain` + never-contain block), and the tripwires converted to passing.
5. **README reconciled** (badges 343→629, Phase 2 conditional-pass status, implementation caveats, built/not-yet lists).
6. **Sprint groupings reconciled** (Task 27 ∈ Sprint 2/Phase 2; Sprint 3 = 28–31 incl. 28a).

> **Lineage note:** the integration task was initially drafted as "Task 27a" (placed before Task 28) and **corrected to Task 28a** with a firm `Depends on: Task 28`. A "27a" label sorts before Task 28 and would re-open the throwaway-wiring path; making Task 28 a hard dependency is what enforces DEC-048 in the plan itself.

---

## Tests requested and verified by the IDE

New file `tests/engine/test_policygate_integration_tripwire.py` — three tests, all
`@pytest.mark.xfail(strict=True, reason="DEC-048 / Task 28a: …")`. All confirmed **XFAIL** (not XPASS, not FAIL) in the closure run.

| # | Test | Behavior |
|---|---|---|
| 1 | **Structural guard** (can't-rot) | asserts `evaluate_policy_gate` appears in `inspect.getsource(orchestrator)`. Absent today → XFAIL. When wiring lands, the symbol appears → XPASS → `strict=True` turns that into a **suite FAILURE**, forcing removal of the marker. Wiring-style-agnostic; this is the safety net. |
| 2 | `test_intake_emits_auto_contain_when_gate_approves` | runs an `auto_contain` judgment through `process_alert_intake`, expects `Disposition.AUTO_CONTAIN`. XFAIL today (skeleton downgrade). Becomes the Task 28a `engine_intake` eval seed (`confirmed_malicious_sequence` analog). |
| 3 | `test_intake_escalates_never_contain_snapshot_when_target_excluded` | never-contain block seed (mirrors `never_contain_target.yaml` / `host_bundle(host_id="dc-01")`), expects escalate with `never_contain_snapshot` fault flag. XFAIL today. |

**Effect:** Sprint 3 cannot close Task 28a without converting the three xfail markers to passing tests. The structural guard guarantees the deferral is visible and trips the moment the wiring is added.

---

## Independent gap hunt (do not rely on the green suite)

| Check | Verdict | Evidence |
|---|---|---|
| **C1 Schema wiring (production path)** | **PASS** (test coverage PARTIAL → T1) | `open_state_store` (`store.py:327-388`) wires annotations + feed-export directly; rate-counter, circuit-breaker, and provider-health tables via `run_engine_startup_recovery → reconcile_policy_state` (`policy/state.py:175-182`). Not fixture-only. |
| **C2 Outcome Matrix canonicality** | **PASS** | `OutcomeMatrixFaultFlag` (`metrics/events.py:34-55`) = all 19 spec §"Outcome Matrix" / contracts §13 rows; `evals/outcome_matrix.py` keys on that enum; `test_outcome_matrix_completeness_guard` asserts `covered == REQUIRED_MATRIX_PAIRS` (exact, not just `>=`); SFE polarity enforced per row. |
| **C3 Self-referential test sweep** | **PARTIAL** → T2 | Eval layer is canonical (flags validated against the enum). Gap: policy-module string literals (`policy/gate.py`, `containment_policy.py`, `identity.py`) are not statically asserted ⊆ `OutcomeMatrixFaultFlag` — only transitive harness coverage enforces it. |
| **C4 Phase 2 gate criteria** | **PASS (isolated) / conditional (production)** | All `docs/plan.md` Phase 2 criteria met at unit/eval level; "PolicyGate blocks unsafe auto_contain", "feed health blocks", "emergency evaluated live", "metrics include feed lag" are true only when the gate/collector are called directly — see F1. |
| **C5 Consumer verifier protocol parity** | **PASS** | `consumer_sdk/reference_verifier.py` implements the §10 pre-actuation order; no fail-open path (failures return ESCALATE_HUMAN/NON_ACTIONABLE). §10 item 6 (local consumer policy) intentionally out of v1 reference scope (`.workflow/TASK-021/final-report.md`). |
| **C6 Deferred-work check** | **PASS** | `docs/plan.md` §Deferred Work items have no silent partial implementations; Task 13 Vertex provider is an intentional stub; real-provider probe correctly probabilistic/non-gating (DEC-047). |

---

## TRACK — real, lower-risk; carry into Task 28a / early Phase 3

### T1. No single test asserts all Phase 2 tables exist via the production open path
**Severity:** Minor · **Source:** IDE (C1) · The code path is correct, but no test opens via `open_production_state_store` + `init_state_dir` (held `SingletonLock`) and asserts `analyst_annotations`, `containment_rate_counters`, `circuit_breaker_state`, `provider_health_metrics`, `revocation_feed_export_meta` all exist without any manual `init_*`. Add one in Task 28a so the wiring chain is pinned, not just exercised.

### T2. Policy-module fault-flag literals not statically pinned to the canonical enum
**Severity:** Minor · **Source:** Claude/IDE (C3) · When Task 28a wires `evaluate_policy_gate` into the orchestrator, add a static assertion that every fault-flag literal the gate/engine can emit is a member of `OutcomeMatrixFaultFlag`. Today drift is caught only transitively (engine output must match scenario expectations, which must be canonical). Make it explicit once the production path emits these flags.

### T3. Behavioral tripwire seeds can "rot" after wiring
**Severity:** Minor · **Source:** Claude · Tripwire tests #2/#3 could remain XFAIL for the wrong reason after wiring if their fixtures don't satisfy the gate. The structural guard (#1) is the can't-rot net; Task 28a acceptance must convert **all three** to passing (markers removed), not just #1.

---

## ACCEPT-AS-DEFERRED — documented, not gate blockers

| # | Item | Basis |
|---|---|---|
| D1 | Consumer §10.6 local-policy check | Intentional v1 scope boundary — consumer-owned (`.workflow/TASK-021/final-report.md`) |
| D2 | `ledger_chain_integrity_failure` harness scenario | Startup refuse-to-start, not harness-runnable (`.workflow/TASK-026/final-report.md`) |
| D3 | Live Gemini adversarial probe in CI | Probabilistic, non-gating by design (DEC-047; `docs/eval_gates.md`) |
| D4 | Org-config numeric per-scope rate ceilings | Future schema; v1 fixed ceiling = 1 (DEC-029) |

---

## Process note — scope guard widened (verified legitimate)

`tests/contracts/test_scope_guard.py` was changed to add `docs/decisions.md` to the allowlist of docs that may change. **Verified legitimate, not a guard-weakening:** per the doc-change hierarchy (`spec.md` frozen; refinements → `decisions.md`), `decisions.md` is a sanctioned edit target, and **`docs/spec.md` remains excluded** so the freeze still holds. Carry-forward: the assertion message still references "Phase 1" and the allowlist will block legitimate Phase 5 docs (`operator_runbook.md`, `architecture.md`, `eval_gates.md` per Task 35) — update the guard's scope when those land.

---

## What each pass got right / missed

| | Claude (verification + audit) | IDE (independent verify + remediate) |
|---|---|---|
| Strength | Ran the full suite; confirmed Outcome Matrix canonicality and production schema wiring against known failure modes; caught F1 (integration/coverage gap the green suite masks) via the scenario→runner mapping | Independently confirmed all findings with file:line evidence; executed the remediation (DEC-028/048, Task 28a, tripwires, README); produced the closure verification |
| Miss | Handed verification to the IDE before finalizing (by design — corroboration over self-assertion) | Initial remediation mislabeled the task "27a" (before Task 28) and hedged the Task 28 dependency — corrected to "28a" with a firm dependency |

The green suite hid F1 because the safety-critical evals call `evaluate_policy_gate` directly rather than through `process_alert_intake`. The tripwires close that blind spot for Sprint 3.

---

## Conditions attached to the conditional pass (carry into Phase 3)
1. **Task 28a** present in `docs/plan.md` — `Depends on: Tasks 17-24, 26, 28`, `Blocks: Task 31 / Phase 3 gate`. ✔ (verify 27a→28a correction landed)
2. **DEC-028 ratified** in `docs/decisions.md`; **DEC-048** deferral recorded. ✔
3. **Three strict-xfail tripwires** present and XFAIL in `tests/engine/test_policygate_integration_tripwire.py`. ✔
4. **Phase 3 gate** requires: PolicyGate + `MetricsCollector` wired into `process_alert_intake` in one serializable emit transaction (DEC-028); end-to-end `engine_intake` evals for gated `auto_contain` + never-contain block; tripwires converted to passing. ✔
5. **README** reconciled; **sprint groupings** consistent (13–27 Phase 2; 28–31 incl. 28a Phase 3). ✔
6. **T1, T2** logged as Task 28a acceptance items; **T3** — all three tripwires must convert to passing, not just the structural guard.
7. **Sprint 3 cannot close Task 28a** while any of the three xfail markers remain.
