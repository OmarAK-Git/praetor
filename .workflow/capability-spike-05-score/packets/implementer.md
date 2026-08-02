# Implementer packet — capability-spike-05-score

## Objective

Add scoring, A/B delta, and confound check.

## Docs

Plan **Task 5** in `docs/superpowers/plans/2026-08-01-judgment-capability-spike.md` (verbatim).

## Allowed files

- evals/capability/score.py
- tests/evals/capability/test_score.py
- .workflow/capability-spike-05-score/

## Do not touch

src/praetor/**, harness, scenarios, agentic. Do not fold PolicyGate into score.

## Instructions

1. TDD Task 5 from plan.
2. Verify green.
3. Do not mark queue done.
4. Commit: `Add capability spike scoring, A/B delta, and confound check.`

Write `results/implementer-result.md`.
