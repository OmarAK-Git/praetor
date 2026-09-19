# eval-kernel-20-github-workflow

**Goal:** Task 20 — GitHub Actions workflow: install .[dev], pytest, and python -m evals.harness --all on FakeProvider; fail on fail/error/missing row; not notebook-only; no Vertex required.

**Scope:** Workflow plus --all CLI verification only. Do not require live Vertex. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- eval-kernel.yml installs .[dev], runs pytest, and runs python -m evals.harness --all.
- Workflow does not require Vertex and is not notebook-only.
- Suite fails the job on fail/error/missing scorecard rows.
- The verifier checks only Task 20 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- .github/workflows/eval-kernel.yml
- evals/harness.py
- tests/evals/test_e2e_kernel.py
- tests/evals/test_eval_kernel_workflow.py
- .workflow/eval-kernel-20-github-workflow/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/test_e2e_kernel.py::test_harness_all_exits_zero_after_full_suite tests/evals/test_eval_kernel_workflow.py -q
- python -m evals.harness --all
- ruff check tests/evals/test_eval_kernel_workflow.py tests/evals/test_e2e_kernel.py
