# Verifier packet — eval-kernel-18-cap-stump

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 18 — cap.stump_parity_guard.

## Acceptance criteria
- path_a_fact_count_stump and stump_pair exist and are McNemar-ready.
- new_build is pending, not pass; no quality-win assertion.
- old_build is recorded honestly (new≈stump or pending new).
- The verifier checks only Task 18 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/test_stump.py tests/evals/e2e/test_cap_stump_parity_guard.py -q
- ruff check evals/stump.py evals/e2e_kernel.py tests/evals/test_stump.py tests/evals/e2e/test_cap_stump_parity_guard.py
- mypy evals/stump.py evals/e2e_kernel.py

## Manual checks
- Disposition-vs-stump is not treated as a Sprint 1 or Sprint 2 primary.

## Implementer result (unevidenced)
.workflow/eval-kernel-18-cap-stump/results/implementer-result.md

Write .workflow/eval-kernel-18-cap-stump/results/verifier-result.md
Outcome: pass | gaps | human_needed
