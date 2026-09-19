# Code review — eval-kernel-18-cap-stump (Task 18)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 18 only (`cap.stump_parity_guard`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `de4109e` (`evals/stump.py`, `evals/e2e_kernel.py`, `evals/e2e_scenarios/cap.stump_parity_guard.yaml`, `tests/evals/test_stump.py`, `tests/evals/e2e/test_cap_stump_parity_guard.py`). HEAD is `de4109e`; working tree matches that commit for those five paths. No `src/praetor/**` edits. No Task 19 YAML. Queue item left `in_progress` (not marked done).

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 18 (through commit, before Task 19)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `cap.stump_parity_guard` (McNemar-ready pairs; must not pass as “judgment beats stump”; honest result is `new≈stump` or pending new)
- `.workflow/eval-kernel-18-cap-stump/packets/code-reviewer.md`
- `.workflow/eval-kernel-18-cap-stump/plan.md` acceptance and `files_allowed`
- `.workflow/autopilot-queue.json` item `eval-kernel-18-cap-stump`

## Blocking findings

None.

## Confirmations (packet)

| Required pin | Result |
|---|---|
| McNemar-ready pairs exist | **Confirmed.** `stump_pair` returns `stump_prediction`, `stump_correct`, `model_bucket`, `model_correct` plus `bag_id` / `frozen_label` / `path_a_fact_count` (`evals/stump.py:31-42`). Unit test pins the four McNemar keys on `standard_review` → `model_bucket="benign"`, `model_correct=False` (`tests/evals/test_stump.py:11-21`). Executor feeds `path_a_fact_count = len(correlated.bundle.facts)` and the intake-proposed disposition into `stump_pair` (`evals/e2e_kernel.py:441-469`). No McNemar cell, scipy, or Sprint 2 primary is implemented. |
| `quality_win_claimed` is `false` | **Confirmed.** Hardcoded `False` in `stump_pair` (`evals/stump.py:41`). YAML pins `quality_win_claimed: false` on both arms (`cap.stump_parity_guard.yaml:16,20`). Unit and e2e tests assert `is False`. `model_correct` is never consulted for status (`e2e_kernel.py:125-160`). |
| `new_build` is `pending`, not `pass` | **Confirmed.** After pin match, `run_e2e_scenario` forces `CAPABILITY_QUALITY_IDS` + `arm == "new_build"` + `status != "fail"` to `status="pending"`, `failure_class="none"` (`evals/e2e_kernel.py:154-160`). This ID is already in `CAPABILITY_QUALITY_IDS` (`evals/scorecard.py:15-17`). E2E asserts `rows["new_build"].status == "pending"` (`test_cap_stump_parity_guard.py:23`). |
| `old_build` recorded honestly | **Confirmed.** `old_build` is `pass` only as the harness pin (paired outcomes emitted + `quality_win_claimed` false), not as a quality win. Honest Sprint 1 alternative used: **pending new**, not a documented `new≈stump` quality claim. On this fixture the pair is stump-correct / model-incorrect (`standard_review` vs `frozen_label=malicious`); that mismatch does not flip status. `_quality_pass_forbidden` returns `False` for this ID (`e2e_kernel.py:74-77`) so `stipulated_capability` does not treat the bag-path/honesty pass as a quality pass. |
| No judgment-beats-stump quality claim | **Confirmed.** YAML description forbids the claim (`cap.stump_parity_guard.yaml:4`). `quality_win_claimed` cannot become `True`. `cite_to_subject_primary_earned` stays hardcoded `False` on this path (`e2e_kernel.py:147`). No disposition-vs-stump primary, no α / T=1.0 inferential arm. |
| Files stayed in allowed scope | **Confirmed.** `de4109e` is the five Task 18 product paths only. Matches Step 5 `git add`. No spec/plan mutation, no `src/`, no `evals/scorecard.py`, no Task 19 files, no queue `done`. Workflow result files are under `.workflow/eval-kernel-18-cap-stump/` (allowed). Memory-bank files were not edited (allowed, unused). |
| TDD coverage is adequate | **Confirmed.** Shipped tests match Task 18 Step 1 verbatim (minus unused `Path` / `validate_scorecard_row` imports in the unit file). Threshold 1→benign / 2→malicious, McNemar key values, e2e `quality_win_claimed` false, pair keys present, `old_build=pass` / `new_build=pending`. Fresh run: 3 passed. |

## Checks

| Check | Result |
|---|---|
| YAML / test / executor match Task 18 snippet | YAML matches Step 3 text. Tests match Step 1 text. `evals/stump.py` matches Step 3 text. Executor follows “same bag as Task 17, then `stump_pair`” (duplicated construction; see Minor #2). Dispatch wired at `e2e_kernel.py:121-122`. Scorecard pin is the one named key. Commit message matches Step 5. |
| Same Path A bag as Task 17 | Fixtures, `anchor_time`, `frozen_label`, and `proposed_disposition` match `cap.baseline_bag_path_a.yaml` (Sysmon `process_chain.json` + Security `successful_logon_4624.json`). `path_a_fact_count = len(correlated.bundle.facts)` as specified. |
| Status rules identical to Task 17 | Pin match → `pass`; quality ID + `new_build` + not fail → `pending`. `stipulated_capability` carve-out extended from `cap.baseline_bag_path_a` to include this ID (required; without it both arms would theater-fail on `status=pass` before the pending override). |
| Writes only allowed files | `de4109e` is stump helper, kernel dispatch/executor, YAML, and the two prescribed tests. Sprint 1 gate not run. |
| Extra product scope | None beyond the required `_quality_pass_forbidden` carve-out for this ID. |
| Verification (this review) | `pytest tests/evals/test_stump.py tests/evals/e2e/test_cap_stump_parity_guard.py -q` → 3 passed in 4.79s; `ruff check` clean; `mypy evals/stump.py evals/e2e_kernel.py` clean. |

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Happy-path e2e would accept a stub** (`tests/evals/e2e/test_cap_stump_parity_guard.py:17-23`). Asserted keys are `quality_win_claimed is False`, presence of `stump_correct` / `model_correct`, `path_a_fact_count >= 1`, and the two statuses. A hardcoded observed dict with those keys, plus the existing pending override, would stay green without calling `correlate_telemetry`, `stump_pair`, or intake. Prescribed Step 1. Pair *values* are pinned only in the unit test on a synthetic call. Track only.

2. **Executor copies Task 17 bag construction instead of calling `_run_cap_baseline`** (`evals/e2e_kernel.py:424-469`). Plan wording is “reuses `_run_cap_baseline` bag construction, then `stump_pair`.” Same fixtures and `correlate_telemetry` + `process_alert_intake` shape; not a shared helper. Drift risk if Task 17’s bag path later changes. Plan-faithful enough for this pin.

3. **`quality_win_claimed` cannot become true even if `model_correct` is true** (`evals/stump.py:41`). Correct for Sprint 1, but the e2e pin would still pass if a later proposed disposition were `escalate` / `auto_contain` on this malicious bag. Honesty then rests on `new_build=pending` and the hardcoded flag, not on an asserted stump/model disagreement. Track only.

## Verdict rationale

Task 18 is the stump-pair honesty pin, not a capability-quality claim. `de4109e` implements the approved helper, YAML, executor, dispatch, and TDD tests. McNemar-ready keys are emitted; `quality_win_claimed` is pinned false; `new_build` is forced `pending`; `old_build` is an honesty `pass` without `scorecard_is_quality_pass=True`; disposition-vs-stump is not treated as a Sprint 1 or Sprint 2 primary. No `files_allowed` breach. **approve**.
