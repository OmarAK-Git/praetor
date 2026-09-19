# Verifier packet — eval-kernel-14-use-ledger

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 14 — use.reconstruct_from_ledger.

## Acceptance criteria
- Both arms pass.
- Ledger reconstruction matches the scorecard-asserted edict fields.
- Inability to rebuild the story is failure_class=harness.
- The verifier checks only Task 14 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_use_reconstruct_from_ledger.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_reconstruct_from_ledger.py
- mypy evals/e2e_kernel.py

## Implementer result (unevidenced)
.workflow/eval-kernel-14-use-ledger/results/implementer-result.md

Write .workflow/eval-kernel-14-use-ledger/results/verifier-result.md
Outcome: pass | gaps | human_needed
