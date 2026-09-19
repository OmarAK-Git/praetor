# Code review — eval-kernel-19-cap-label-leak (Task 19)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 19 only (`cap.no_label_leak_ids`). Sprint 1 gate and Task 20 ignored.
**Diff reviewed:** commit `475d692` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/cap.no_label_leak_ids.yaml`, `tests/evals/e2e/test_cap_no_label_leak_ids.py`, `tests/evals/test_e2e_kernel.py`, plus allowed memory-bank pointers and `implementer-result.md`). `evals/theater.py` unchanged. No `src/praetor/**` edits. Queue item left `in_progress` (not marked done).

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 19 (through commit, before Task 20)
- `.workflow/eval-kernel-19-cap-label-leak/packets/code-reviewer.md`
- `.workflow/eval-kernel-19-cap-label-leak/plan.md` acceptance and `files_allowed`
- `.workflow/eval-kernel-19-cap-label-leak/results/implementer-result.md`

## Blocking findings

None.

## Confirmations (packet)

| Required pin | Result |
|---|---|
| Both arms pass (not pending) | **Confirmed.** ID is excluded from `CAPABILITY_QUALITY_IDS` (`evals/scorecard.py:15-17` is only `cap.baseline_bag_path_a` and `cap.stump_parity_guard`). Pending override at `evals/e2e_kernel.py:158-164` therefore does not fire. YAML pins `label_leak_found: false` on both arms. E2E asserts `status == "pass"` and `failure_class == "none"` for `{old_build, new_build}` (`tests/evals/e2e/test_cap_no_label_leak_ids.py:15-19`). |
| Ground-truth stays harness-side; no leak in `excerpt_blob` or `alert_identity` | **Confirmed.** `expected_class`, seed `EventRecordID`, and frozen label live only under YAML `setup.hidden_ground_truth` (`cap.no_label_leak_ids.yaml:11-13`). Executor never passes that dict into `build_judgment_prompt_payload` (`e2e_kernel.py:492-497`). `alert_identity` is the scenario id string (`yaml:7`, executor `:499`). Pin test forbids `"expected_class"` and `"EventRecordID=1001"` in `excerpt_blob` and `"malicious"` in `alert_identity`. Theater needles (`expected_class`, `EventRecordID`, `ground-truth`, `ground_truth`) are not in the provider payload path. |
| Leak would be `failure_class=theater_detector` | **Confirmed** for detector-defined leaks. Executor ORs `finding.tripped` into `label_leak_found` (`e2e_kernel.py:516-519`). Kernel then re-runs `scenario.theater_detector` (`label_leak`) on the **observed** `excerpt_blob` / `alert_identity` (`e2e_kernel.py:141-144`, `:154-156`) and, on trip, overwrites `failure_class="theater_detector"`. That observed-excerpt wiring is new in this commit and is what makes an excerpt leak a theater fail rather than a pin/`harness` fail. Value-only extras (`"malicious"` in excerpt, `"1001"` in identity) without a needle match stay `harness` — see Minor #1. |
| All 15 required scenario IDs exist on disk | **Confirmed.** `evals/e2e_scenarios/` has exactly the 15 locked IDs in `REQUIRED_E2E_SCENARIO_IDS` (`e2e_kernel.py:45-63`). `test_required_ids_are_the_locked_fifteen` pins that set. |
| Full suite emits 30 rows and `kernel_exit_code` 0 | **Confirmed.** `test_full_suite_has_thirty_rows_and_exits_zero` (`test_e2e_kernel.py:75-79`) asserts `len(rows)==30`, id set equality, and `kernel_exit_code(rows)==0`. Pending quality `new_build` rows do not fail the exit (`e2e_kernel.py:900-902` only fails on `fail`/`error`). `--e2e` CLI test now expects returncode 0 and prints `cap.no_label_leak_ids`. |
| `test_harness_e2e_flag_exits_nonzero_on_empty_kernel` replaced; empty-dir unit test kept | **Confirmed.** Replaced by `test_harness_e2e_flag_exits_zero_after_full_suite` (`test_e2e_kernel.py:62-72`). `test_empty_directory_emits_harness_error_rows` still uses a temp dir and still expects exit 1 (`:41-53`). Old name is gone from live tests. |
| Files stayed in allowed scope | **Confirmed.** `475d692` touches only allowed paths: kernel, YAML, both test files, memory-bank pointers, and `.workflow/eval-kernel-19-cap-label-leak/results/implementer-result.md`. `evals/theater.py` not modified. No spec/plan mutation, no `src/`, no scorecard membership change, no queue `done`. |
| TDD coverage is adequate | **Confirmed** against the approved Step 1 test (verbatim) plus the prescribed closure and `--e2e` replacement. Tests invoke the real kernel / CLI; a missing YAML, missing executor, pending override, or theater trip would fail them. No negative e2e that injects a leak — see Minor #2. Matches sibling theater-pin tests. |

## Checks

| Check | Result |
|---|---|
| YAML / test / executor match Task 19 snippet | YAML matches Step 3 text. Pin test matches Step 1 text. Executor matches Step 3 (`_run_cap_no_leak` named `_run_cap_no_label_leak_ids` to match sibling naming). Dispatch wired at `e2e_kernel.py:123-124`. Scorecard pin is the one named key. Commit message matches Step 5. |
| Not in `CAPABILITY_QUALITY_IDS`; no forced pending | This ID is absent from the frozenset. `_quality_pass_forbidden` cannot treat it as a quality pass. |
| Theater detector consumed | Inner `run_theater_detector("label_leak", ...)` plus YAML `theater_detector: label_leak` on the shared kernel path. Needles unchanged in `evals/theater.py:13`. |
| Writes only allowed files | `475d692` product files match Step 5 `git add` plus allowed memory-bank / workflow result. Sprint 1 gate not run. |
| Extra product scope | Kernel now forwards observed `excerpt_blob` / `alert_identity` into the shared theater context (was `excerpt_blob=""`). Required for excerpt leaks to become `theater_detector`. Only other executor that returns `excerpt_blob` is `thr.instruction_in_cmdline` (`stipulated_capability`), which does not read the blob. No suite break (30 rows, exit 0). |
| Verification (this review) | `pytest tests/evals/e2e/test_cap_no_label_leak_ids.py tests/evals/test_e2e_kernel.py::test_required_ids_are_the_locked_fifteen tests/evals/test_e2e_kernel.py::test_full_suite_has_thirty_rows_and_exits_zero tests/evals/test_e2e_kernel.py::test_empty_directory_emits_harness_error_rows tests/evals/test_e2e_kernel.py::test_harness_e2e_flag_exits_zero_after_full_suite -q` → 5 passed in 14.35s. |

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Value-only extras classify as `harness` unless a theater needle also matches** (`evals/e2e_kernel.py:516-519`, `evals/theater.py:13-55`). Executor ORs `"malicious"` in `excerpt_blob` and `"1001"` in `alert_identity` into `label_leak_found`. Those strings are not `_LEAK_NEEDLES`. Pin mismatch then sets `failure_class="harness"`; the outer remap to `theater_detector` only runs when `_label_leak` trips (`expected_class`, `EventRecordID`, `ground-truth`, `ground_truth`). Plan sample is identical. Field-name leaks still become `theater_detector` because this commit forwards observed excerpts into the shared detector. Track only.

2. **No e2e that injects a leak and asserts `failure_class=theater_detector`** (`tests/evals/e2e/test_cap_no_label_leak_ids.py`). Prescribed Step 1 is happy-path only. Trip behavior is pinned in `tests/evals/test_theater.py:31-37` and remapped in `run_e2e_scenario`. A stub that returned `label_leak_found=False` plus a clean excerpt would still pass the pin test; the full-suite exit-0 test is what forces a real executor. Same TDD shape as other theater pins. Track only.

## Verdict rationale

Task 19 is the 15th locked theater pin, not a capability-quality claim. `475d692` implements the approved YAML, executor, dispatch, observed-excerpt theater wiring, and the `--e2e` / 30-row closure tests. Both arms `pass`; ground-truth stays in `setup.hidden_ground_truth`; detector trips remap to `theater_detector`; all 15 IDs are on disk; the full suite is 30 rows with `kernel_exit_code` 0. No `files_allowed` breach. **approve**.
