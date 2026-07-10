# Implementer Packet — V2-036 Eval Regression Locking Discipline

**implementation_model:** composer-2.5-fast

## Objective

Workflow template requires confirmed model errors → harness scenario or waiver. Eval gate docs for scenario quality + expectation-key validation. CI guard for stale/unknown expectation keys.

## Allowed files

- `.workflow/_template/`, `evals/`, `docs/eval_gates.md`, `tests/evals/`, `specs/`, `memory-bank/`

## Verification

pytest tests/evals/ -q

Write `.workflow/v2-036-eval-regression/results/implementer-result.md`. Do NOT mark queue done.
