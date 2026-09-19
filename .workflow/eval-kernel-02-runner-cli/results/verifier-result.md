# Verifier result — eval-kernel-02-runner-cli (Task 2)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 2 is done — `evals.e2e_kernel` skeleton + harness `--e2e`/`--all`, default no-arg path still Outcome Matrix only, locked 15 IDs, no Path B import.

Implementer result (`implemented`, pytest 50 / ruff / mypy green) was treated as unevidenced until re-run.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| `python -m evals.harness` with no args still runs only the Outcome Matrix suite | **met** | Fresh invocation (this session): exit **0**, 34 `[PASS]` OM scenario lines (`account_containment_enabled` … `ticket_stamp_failed`). No kernel `[ERROR]` rows, no `failure_class=harness`, no locked E2E IDs. Code: `evals/harness.py:1317-1323` — `run_matrix` true and `run_kernel` false when `--e2e`/`--all` absent. Pytest: `test_harness_default_still_runs_outcome_matrix_only` and existing `test_harness_main_exits_zero_on_success`. Accidental kernel run on the empty `e2e_scenarios/` dir would OR exit 1. |
| `--e2e` and `--all` are recognized on the same CLI | **met** | Same `main()` in `evals/harness.py:1317-1345`. Fresh `--e2e`: exit **1**, 15 kernel `[ERROR]` missing-file rows only — no OM `[PASS]` lines. Fresh `--all`: 34 OM `[PASS]` lines then 15 kernel `[ERROR]` rows, exit **1** (OM 0 OR kernel 1). Pytest: `test_harness_e2e_flag_exits_nonzero_on_empty_kernel`. |
| `REQUIRED_E2E_SCENARIO_IDS` lists the locked 15 IDs | **met** | `evals/e2e_kernel.py:13-31` equals spec §5 (`docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md:163-205`): 3 cap / 3 gov / 3 des / 3 thr / 3 use. Pinned by `test_required_ids_are_the_locked_fifteen`. |
| `evals.e2e_kernel` does not import `evals.capability.flatten` | **met** | Read `evals/e2e_kernel.py` end-to-end. Imports are `__future__`, `collections.abc.Sequence`, `pathlib.Path`, and `evals.scorecard` (`Realm`, `ScorecardRow`, `validate_scorecard_row`). No `evals.capability*`, no `flatten`, no `importlib` / `__import__`. The string `"capability"` appears only as a realm map value (`:34-39`). Kernel import in harness is lazy inside the `--e2e`/`--all` branch (`harness.py:1336`). |
| Verifier checks only Task 2 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set plus short CLI invocations of `evals.harness`. No sprint-exit / CI / scenario-YAML / executor checks. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/test_e2e_kernel.py tests/evals/test_eval_harness.py -q` | **0** | 50 passed in 24.25s |
| `ruff check evals/e2e_kernel.py evals/harness.py tests/evals/test_e2e_kernel.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py evals/harness.py` | **0** | Success: no issues found in 2 source files |
| `python -m evals.harness` | **0** | 34 OM `[PASS]` lines; no kernel output |
| `python -m evals.harness --e2e` | **1** | 15 kernel `[ERROR]` missing-file rows; no OM output |
| `python -m evals.harness --all` | **1** | 34 OM `[PASS]` then 15 kernel `[ERROR]` rows |

Re-run in this session against the current working tree. Implementer transcript was not treated as evidence.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Default no-arg harness path unchanged | **met** | Independent no-arg invocation above. Output is the existing OM fixture set, not E2E scorecards. |
| No Path B import on the kernel module | **met** | File read of `evals/e2e_kernel.py` (see AC row). `evals/scorecard.py` also has no flatten import. |
| No scenario YAML / executors added | **met** | `evals/e2e_scenarios/` contains only `.gitkeep`. `run_e2e_kernel` (`e2e_kernel.py:79-87`) glob `*.yaml` and emit missing-id harness errors; `tmp_root` unused (skeleton). |

## Gaps

None that fail Task 2 acceptance.

Residual (non-blocking, not Task 2 AC):

- `--all` has no pytest pin; deleting the `--all` branch would still leave the packet tests green. Fresh CLI invocation in this session covers the flag.
- No static “kernel must not import flatten” test. Inspection of `evals/e2e_kernel.py` is the packet check.
- `test_harness_default_still_runs_outcome_matrix_only` asserts only exit 0 (stdout not pinned). Independent no-arg invocation showed the OM suite.
