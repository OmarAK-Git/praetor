# Verifier packet — eval-kernel-16-use-demo-honesty

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 16 — use.demo_honesty_gate.

## Acceptance criteria
- Both arms pass when demo copy does not claim unearned judgment.
- Unearned capability claims trip theater_detector unearned_demo_claim.
- A stump-only win is not treated as a claim.
- The verifier checks only Task 16 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_use_demo_honesty_gate.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_demo_honesty_gate.py
- mypy evals/e2e_kernel.py

## Implementer result (unevidenced)
.workflow/eval-kernel-16-use-demo-honesty/results/implementer-result.md

Write .workflow/eval-kernel-16-use-demo-honesty/results/verifier-result.md
Outcome: pass | gaps | human_needed
