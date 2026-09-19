# Code review — eval-kernel-20-github-workflow (Task 20)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 20 only (GitHub Actions FakeProvider merge gate). Sprint 1 gate and Task 21 docs pointer ignored.
**Diff reviewed:** commit `93756eb` (`.github/workflows/eval-kernel.yml`, `tests/evals/test_e2e_kernel.py`, `tests/evals/test_eval_kernel_workflow.py`, `memory-bank/activeContext.md`, plus `implementer-result.md`). `evals/harness.py` unchanged. `walkthrough.yml` / `demo-pages.yml` not in the commit. Queue item left `in_progress` (not marked done).

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 20 (through commit, before Task 21)
- `.workflow/eval-kernel-20-github-workflow/packets/code-reviewer.md`
- `.workflow/eval-kernel-20-github-workflow/plan.md` acceptance and `files_allowed`
- `.workflow/eval-kernel-20-github-workflow/results/implementer-result.md`

## Blocking findings

None.

## Confirmations (packet)

| Required pin | Result |
|---|---|
| `eval-kernel.yml` installs `.[dev]`, runs `pytest tests/evals/`, runs `python -m evals.harness --all` | **Confirmed.** YAML matches the Task 20 Step 3 snippet. Install is `python -m pip install -e ".[dev]"` (`eval-kernel.yml:23-25`). Pytest step is `python -m pytest tests/evals/ -q` (`:27-28`). Harness step is `python -m evals.harness --all` (`:30-31`). GHA fails the job on nonzero by default; no `continue-on-error`. |
| No Vertex secret / `PRAETOR_REAL_PROVIDER_PROBE` / `PRAETOR_CAPABILITY_SPIKE` | **Confirmed.** Workflow has no `secrets:`, no Vertex/GCP/ADC env, and neither probe/spike flag. `[dev]` extras are pytest/mypy/ruff/types-PyYAML/pysigma only (`pyproject.toml:16-23`). Kernel probe path stays opt-in (`evals/e2e_kernel.py:812`) and is unset here. |
| Not notebook-only (no `nbconvert`) | **Confirmed.** `eval-kernel.yml` has no `nbconvert` / `nbclient` / notebook execute step. Guarded by `test_eval_kernel_workflow_is_not_notebook_only`. |
| `--all` exits 0 on FakeProvider | **Confirmed.** Prescribed `test_harness_all_exits_zero_after_full_suite` actually runs `python -m evals.harness --all`. OM scenario IDs do not include `gov.never_contain_live_shape` or `cap.baseline_bag_path_a`, so those stdout pins cannot pass on the default OM-only path. `harness.main` ORs matrix + `kernel_exit_code` (`evals/harness.py:1317-1345`). This review: 2 passed in 13.15s. |
| Existing `walkthrough.yml` / `demo-pages.yml` were not replaced as the only CI | **Confirmed.** Both files still exist and are absent from `93756eb`. `walkthrough.yml` remains the notebook/`nbconvert` job; `demo-pages.yml` remains Pages publish. New workflow is additive. |
| Files stayed in allowed scope | **Confirmed.** `93756eb` touches only allowed paths: workflow YAML, the two test files, `memory-bank/activeContext.md`, and `.workflow/eval-kernel-20-github-workflow/results/implementer-result.md`. `evals/harness.py` not modified (print-separator optional). No `src/`, no `docs/eval_gates.md` (Task 21), no queue `done`. |

## Checks

| Check | Result |
|---|---|
| Workflow YAML vs Task 20 snippet | Byte-for-byte match of the approved Step 3 YAML (name, comments, `on`, ubuntu-latest, Python 3.12, three run steps). |
| Prescribed tests vs Step 1 | `test_harness_all_exits_zero_after_full_suite` and `test_eval_kernel_workflow_is_not_notebook_only` match the plan text. |
| Fail/error/missing row fails the job | Not reimplemented in Task 20. `--all` uses existing `kernel_exit_code` (`evals/e2e_kernel.py:892-902`) which returns 1 on missing required ID or any `fail`/`error`; `main` returns 1 if either half is nonzero. Workflow step inherits that exit. |
| FakeProvider only | No Vertex install or secret. Capability-spike / real-provider tests under `tests/evals/` stay default-deselected via `addopts = '-m "not integration and not probabilistic"'` (`pyproject.toml:35`) or env-unset skip paths. |
| Extra product scope | None. Status line in `activeContext.md` only. |
| Verification (this review) | `pytest tests/evals/test_e2e_kernel.py::test_harness_all_exits_zero_after_full_suite tests/evals/test_eval_kernel_workflow.py -q` → 2 passed in 13.15s. |

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Workflow guard is substring-only** (`tests/evals/test_eval_kernel_workflow.py:13-20`). The prescribed test would still pass if the required strings lived in comments, or if a later edit added `secrets:`, a Vertex env, or `continue-on-error: true`. Inspection of `eval-kernel.yml` is clean. Track only; do not expand the test beyond the plan unless a later task owns a stronger static scan.

2. **`memory-bank/tasks.md` and `memory-bank/progress.md` still say next is Task 20** while `activeContext.md` now points at Task 21. Both status files were in `files_allowed`. Not a product defect; Task 21 already owns `tasks.md`.

## Verdict rationale

Task 20 is the FakeProvider CI gate, not a kernel behavior change. `93756eb` lands the approved workflow YAML and the two prescribed tests, leaves `evals/harness.py` and the notebook/demo workflows untouched, and does not introduce Vertex or probe/spike env. `--all` is now exercised as a real subprocess (closing the Task 2 review note that the flag was untested). No `files_allowed` breach. **approve**.
