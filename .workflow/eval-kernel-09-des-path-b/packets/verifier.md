# Verifier packet — eval-kernel-09-des-path-b

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 9 — des.path_b_stays_out_of_src.

## Acceptance criteria
- Both arms pass.
- src/praetor import of evals.capability.flatten or a Path B flattener is a theater_detector fail.
- Path B remains under evals/.
- The verifier checks only Task 9 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_des_path_b_stays_out_of_src.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_path_b_stays_out_of_src.py
- mypy evals/e2e_kernel.py

## Manual checks
- No src/praetor/ Path B import added.

## Implementer result (unevidenced)
.workflow/eval-kernel-09-des-path-b/results/implementer-result.md

Write .workflow/eval-kernel-09-des-path-b/results/verifier-result.md
Outcome: pass | gaps | human_needed
