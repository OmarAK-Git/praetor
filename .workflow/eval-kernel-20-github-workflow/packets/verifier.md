# Verifier packet — eval-kernel-20-github-workflow

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 20 — GitHub Actions workflow.

## Acceptance criteria
- eval-kernel.yml installs .[dev], runs pytest, and runs python -m evals.harness --all.
- Workflow does not require Vertex and is not notebook-only.
- Suite fails the job on fail/error/missing scorecard rows.
- The verifier checks only Task 20 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/test_e2e_kernel.py::test_harness_all_exits_zero_after_full_suite tests/evals/test_eval_kernel_workflow.py -q
- python -m evals.harness --all
- ruff check tests/evals/test_eval_kernel_workflow.py tests/evals/test_e2e_kernel.py

Write .workflow/eval-kernel-20-github-workflow/results/verifier-result.md
Outcome: pass | gaps | human_needed
