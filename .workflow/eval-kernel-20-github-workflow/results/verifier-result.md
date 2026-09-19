# Verifier result — eval-kernel-20-github-workflow (Task 20)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 20 is done — `.github/workflows/eval-kernel.yml` installs `.[dev]`, runs pytest on `tests/evals/`, and runs `python -m evals.harness --all`; the workflow does not require Vertex and is not notebook-only; the suite fails the job on fail/error/missing scorecard rows.

Implementer results (`2 passed`, harness exit 0, ruff green, “no Vertex secret”) were treated as unevidenced until re-run and re-read this session.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| `eval-kernel.yml` installs `.[dev]`, runs pytest, and runs `python -m evals.harness --all` | **met** | Live file `.github/workflows/eval-kernel.yml:22-31`: `python -m pip install -e ".[dev]"`, `python -m pytest tests/evals/ -q`, `python -m evals.harness --all`. No `continue-on-error`. `pyproject.toml:16-23` defines `dev` extras including pytest. Prescribed guard `tests/evals/test_eval_kernel_workflow.py:13-17` asserts those three needles. |
| Workflow does not require Vertex and is not notebook-only | **met** | `eval-kernel.yml` has no `secrets.`, `env:`, `VERTEX`, `GOOGLE_`, `GEMINI`, `nbconvert`, `PRAETOR_REAL_PROVIDER_PROBE`, or `PRAETOR_CAPABILITY_SPIKE` (full-file read + grep). Comment at `:3-4` states notebook/demo workflows are not a substitute. Sibling CI still exists: `.github/workflows/walkthrough.yml` (nbconvert notebook job) and `demo-pages.yml`. Real-provider tests under `tests/evals/` mock `urlopen` or are `@pytest.mark.integration` + `probabilistic` (excluded by `addopts` in `pyproject.toml:35`). |
| Suite fails the job on fail/error/missing scorecard rows | **met** | `kernel_exit_code` (`evals/e2e_kernel.py:892-902`) returns 1 on missing required ID (both arms absent) or any `status` in `{fail, error}`. Missing files emit `status=error` / `failure_class=harness` (`:872-889`, `:922`). `harness.main` ORs matrix + kernel codes (`evals/harness.py:1343-1345`). This session: constructed 15-ID sets → `one_fail=1`, `one_error=1`, `drop_one_id=1`, `one_pending=0`, `thirty_pass=0`; patched `harness.main(['--all'])` → `main_all_one_fail=1`, `main_all_one_error=1`, `main_all_missing=1`. GHA fails the step on nonzero (no `continue-on-error`). |
| Verifier checks only Task 20 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set plus independent fail-path probes of `kernel_exit_code` / `harness.main`. Full `pytest tests/evals/` and Sprint 1 / phase-exit suite not treated as Task 20 AC. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/test_e2e_kernel.py::test_harness_all_exits_zero_after_full_suite tests/evals/test_eval_kernel_workflow.py -q` | **0** | `..` — 2 passed in 17.66s (no skips) |
| `python -m evals.harness --all` | **0** | 34 OM `[PASS]` lines + 30 kernel scorecard lines; `cap.baseline_bag_path_a` / `cap.stump_parity_guard` `new_build` printed `[PENDING]` |
| `ruff check tests/evals/test_eval_kernel_workflow.py tests/evals/test_e2e_kernel.py` | **0** | All checks passed |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~17.7s) is consistent with a real `--all` subprocess (the named test shells `python -m evals.harness --all`). Count is from the live `-q` run, not `--collect-only`.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| No Vertex secret | **met** | Entire `eval-kernel.yml` (32 lines) has no `secrets.`, no Vertex/Gemini/Google credentials, no provider env. |
| No `PRAETOR_REAL_PROVIDER_PROBE` or `PRAETOR_CAPABILITY_SPIKE` | **met** | Absent from `eval-kernel.yml`. Asserted by `test_eval_kernel_workflow.py:19-20`. Kernel live-half stays `not_requested` unless the probe env is `1` (`evals/e2e_kernel.py:811-813`). |
| No nbconvert | **met** | Absent from `eval-kernel.yml`. Present only on the separate walkthrough job (`walkthrough.yml:36-44`). Asserted by `test_eval_kernel_workflow.py:18`. |
| `walkthrough.yml` is not the only CI | **met** | Three workflows on disk: `eval-kernel.yml`, `walkthrough.yml`, `demo-pages.yml`. Eval-kernel is an independent push/PR/`workflow_dispatch` job (`eval-kernel.yml:6-10`). |

## Independent probes (not in packet)

- Live `--all` this session: 34 Outcome Matrix PASS + 15 scenarios × 2 arms = 30 kernel rows; quality `new_build` rows are the only `[PENDING]`; process exit 0.
- `kernel_exit_code` on a complete 15-ID one-arm set: pass→0; one `fail`→1; one `error`→1; one `pending`→0; drop one required ID→1; 30-row all-pass→0; 30-row one-fail→1.
- In-process `harness.main(['--all'])` with patched kernel rows: fail, error, and all-missing helper rows each return 1 (GitHub Actions then fails the job).
- Workflow file matches the Task 20 Step 3 snippet (`docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md:3451-3482`). CLI test matches Step 1 (`test_e2e_kernel.py:93-103`). Product files committed as `93756eb` (`ci: add FakeProvider eval-kernel workflow for pytest and E2E suite`); working tree clean for those paths.
- `evals/harness.py` was not required to change for Task 20 (`--all` already ORs matrix + kernel codes).

## Gaps

None that fail Task 20 acceptance.

Residual (non-blocking, not Task 20 AC failures):

- `test_eval_kernel_workflow.py` is a substring guard. A comment-only copy of the needles would satisfy the test; the live YAML puts them in `run:` steps, which this session read.
- Packet pytest does not exercise the fail/error/missing path. Those exits were proven here via `kernel_exit_code` and patched `harness.main`, not by deleting a scenario file on disk.
- GitHub-hosted runner was not executed. Job-fail behavior is inferred from GHA default (nonzero step fails) plus no `continue-on-error`.
- Full `pytest tests/evals/` (what the workflow job runs) was not re-run; out of packet and out of Sprint 1 gate scope.

Queue item status was not updated (implementer packet: do not mark done).
