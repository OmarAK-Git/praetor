# Code review — eval-kernel-02-runner-cli (Task 2)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 2 only (e2e_kernel skeleton + harness `--e2e` / `--all`). Sprint 1 gate gaps ignored.
**Diff reviewed:** commit `c3101a8` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/.gitkeep`, `evals/harness.py`, `tests/evals/test_e2e_kernel.py`) plus current disk contents of those four files. Working tree matches `c3101a8` for the product files. Uncommitted tree also has `.workflow/autopilot-queue.json` and `.workflow/eval-kernel-02-runner-cli/` orchestration files; those are out of product scope and were not treated as Task 2 defects.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 2
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §4 harness architecture
- `.workflow/eval-kernel-02-runner-cli/packets/code-reviewer.md`
- `.workflow/eval-kernel-02-runner-cli/plan.md` acceptance

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Default no-arg OM path unchanged | `main` runs Outcome Matrix unless `--e2e` is present without `--all`. `test_harness_default_still_runs_outcome_matrix_only` + existing `test_harness_main_exits_zero_on_success` both exit 0. Accidental kernel run would OR a nonzero kernel code and fail those tests. |
| `--e2e` / `--all` | `--e2e` → kernel only; `--all` → OM then kernel and OR exit codes (`evals/harness.py:1317-1345`). Matches the plan snippet. |
| 15 locked IDs | `REQUIRED_E2E_SCENARIO_IDS` equals the plan/spec §5 set (3 cap / 3 gov / 3 des / 3 thr / 3 use). Pinned by `test_required_ids_are_the_locked_fifteen`. |
| No Path B import | `evals/e2e_kernel.py` imports only `evals.scorecard`. No `evals.capability*` / flatten / bundle import. Harness Path B import surface unchanged; kernel import is lazy inside the `--e2e`/`--all` branch. No second `python -m evals.e2e_kernel` entrypoint. |
| Missing IDs are harness errors | Empty dir → one `status=error` / `failure_class=harness` / `arm=old_build` row per missing ID; `kernel_exit_code` is 1. `--e2e` subprocess exits 1 and prints `gov.never_contain_live_shape`. |
| Writes only allowed files | `c3101a8` touches only the four Task 2 product files. No `src/praetor/**`, no scenario YAML, no Path B modules. |
| Extra product scope | None (no executors, no CBC/envelope, no CI workflow). |
| Verification (this review) | `pytest tests/evals/test_e2e_kernel.py tests/evals/test_eval_harness.py::test_harness_main_exits_zero_on_success -q` → 6 passed; `ruff check` clean; `mypy evals/e2e_kernel.py evals/harness.py` clean. |

Implementation matches the approved Task 2 snippet (Realm-typed `_REALM_BY_PREFIX` instead of `str` + `# type: ignore`). Disk files match `c3101a8`.

## Non-blocking notes

1. **`--all` is implemented but untested** (`evals/harness.py:1321-1323`, `tests/evals/test_e2e_kernel.py`). Deleting the `--all` branches would leave every Task 2 test green. Task 20 owns the `--all` subprocess test; until then this flag is review-only.

2. **No static “no Path B import” test** (`tests/evals/test_e2e_kernel.py`). The sprint file table lists that theme on this module; Task 2’s prescribed tests do not. Inspection is clean. Task 9 / `path_b_in_src` is the planned pin — do not treat this as delivered coverage.

3. **`kernel_exit_code` uses the weaker “neither arm” reading** (`evals/e2e_kernel.py:66-76`). A required ID with only `old_build` present does not trip the pair check; only `{fail, error}` status does. This is the plan snippet. Later both-arm work must not treat a single passing `old_build` row as suite-complete.

4. **Discovery of present YAML stems is untested.** `run_e2e_kernel` globs `*.yaml` and omits those stems from missing-id rows (`evals/e2e_kernel.py:86-87`). Task 2 tests only the empty-directory path. A broken glob would still pass today.

5. **`test_scorecards_for_missing_ids_are_harness_errors` does not pin `status=="error"`** (`tests/evals/test_e2e_kernel.py:56-59`). `failure_class=harness` with `status=fail` would still pass that test. The empty-directory test covers `error`; keep both when the helper grows.

6. **Interfaces list `CAPABILITY_QUALITY_IDS` as consumed; Task 2 does not import it.** Matches the plan’s own Step 3 snippet. Honesty rules stay on `validate_scorecard_row` — later real runs must keep calling it.
