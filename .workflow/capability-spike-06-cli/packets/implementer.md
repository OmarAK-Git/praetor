# Implementer packet — capability-spike-06-cli

## Objective

Add offline-safe capability spike CLI and document as non-gating.

## Docs

Plan **Task 6** in `docs/superpowers/plans/2026-08-01-judgment-capability-spike.md` (verbatim).

Also: while editing the plan is out of scope, if you touch runner docs in comments only that's fine. Do NOT import agentic. Must not be imported by harness.

## Allowed files

- evals/capability_spike.py
- tests/evals/capability/test_cli.py
- docs/eval_gates.md
- .workflow/capability-spike-06-cli/

## Do not touch

src/praetor/**, evals/harness.py, evals/scenarios/**

## Instructions

1. TDD Task 6 from plan.
2. Append non-gating section to docs/eval_gates.md per plan.
3. Verify commands green including `python -m evals.capability_spike` skip path.
4. Do not mark queue done.
5. Commit: `Add capability spike CLI with offline-safe default.`

Write `results/implementer-result.md`.
