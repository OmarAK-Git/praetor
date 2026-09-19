# Verifier packet — eval-kernel-04-theater

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 4 — Theater detector registry.

## Acceptance criteria
- THEATER_DETECTOR_NAMES includes all six spec §8 names.
- Each named check has a unit test that trips and one that stays clean.
- Unknown detector names raise a harness error.
- The verifier checks only Task 4 acceptance, not Sprint 1 gate completion.

## Changed files
- evals/theater.py
- tests/evals/test_theater.py

## Commands
- pytest tests/evals/test_theater.py -q
- ruff check evals/theater.py tests/evals/test_theater.py
- mypy evals/theater.py

## Manual checks
- No silent skip path in the registry.

## Implementer result (unevidenced)
.workflow/eval-kernel-04-theater/results/implementer-result.md

Write .workflow/eval-kernel-04-theater/results/verifier-result.md
Outcome: pass | gaps | human_needed
