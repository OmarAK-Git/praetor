# Verifier packet — eval-kernel-12-thr-wrong-process

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 12 — thr.valid_cite_wrong_process.

## Acceptance criteria
- Both arms pass the Sprint 1 authority pin.
- Citations resolve but omit the subject Path A fact; that miss is recorded.
- No cite-to-subject McNemar or Sprint 2 primary scoring is implemented.
- The verifier checks only Task 12 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_thr_valid_cite_wrong_process.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_thr_valid_cite_wrong_process.py
- mypy evals/e2e_kernel.py

## Manual checks
- Cite-to-subject remains Sprint 2 PRIMARY, not implemented here.

## Implementer result (unevidenced)
.workflow/eval-kernel-12-thr-wrong-process/results/implementer-result.md

Write .workflow/eval-kernel-12-thr-wrong-process/results/verifier-result.md
Outcome: pass | gaps | human_needed
