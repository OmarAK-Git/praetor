# Verifier packet — eval-kernel-07-gov-recovery

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 7 — gov.recovery_never_contains.

## Acceptance criteria
- Both arms pass on FakeProvider.
- Recovery never emits auto_contain.
- Pin uses run_engine_startup_recovery / recovery resolver, not a PolicyGate-only shortcut.
- The verifier checks only Task 7 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_gov_recovery_never_contains.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_recovery_never_contains.py
- mypy evals/e2e_kernel.py

## Implementer result (unevidenced)
.workflow/eval-kernel-07-gov-recovery/results/implementer-result.md

Write .workflow/eval-kernel-07-gov-recovery/results/verifier-result.md
Outcome: pass | gaps | human_needed
