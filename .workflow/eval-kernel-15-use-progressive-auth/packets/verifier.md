# Verifier packet — eval-kernel-15-use-progressive-auth

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 15 — use.progressive_auth_report.

## Acceptance criteria
- Both arms pass.
- Report reads evaluation rows from the same intake and is read-only.
- A missing evaluation row is a harness fail.
- The verifier checks only Task 15 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_use_progressive_auth_report.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_progressive_auth_report.py
- mypy evals/e2e_kernel.py

## Implementer result (unevidenced)
.workflow/eval-kernel-15-use-progressive-auth/results/implementer-result.md

Write .workflow/eval-kernel-15-use-progressive-auth/results/verifier-result.md
Outcome: pass | gaps | human_needed
