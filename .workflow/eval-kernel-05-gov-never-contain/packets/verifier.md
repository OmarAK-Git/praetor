# Verifier packet — eval-kernel-05-gov-never-contain

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 5 — Kernel executor + gov.never_contain_live_shape.

## Acceptance criteria
- Scenario uses runner e2e_kernel and the production intake call shape.
- old_build and new_build both pass on FakeProvider.
- auto_contain is blocked by live never-contain on process_alert_intake, not a PolicyGate-only shortcut.
- The verifier checks only Task 5 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_gov_never_contain_live_shape.py tests/evals/test_e2e_kernel.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_never_contain_live_shape.py
- mypy evals/e2e_kernel.py

## Manual checks
- No CBC JSON or extra AlertEnvelope fields.
- Outcome Matrix runners unchanged.

## Implementer result (unevidenced)
.workflow/eval-kernel-05-gov-never-contain/results/implementer-result.md

Write .workflow/eval-kernel-05-gov-never-contain/results/verifier-result.md
Outcome: pass | gaps | human_needed
