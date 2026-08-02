# Implementer packet — capability-spike-03-bundle

## Objective

Add Path B bundle builder that reuses correlation window and host filters, then flattens all event types.

## Docs

- Plan **Task 3** in `docs/superpowers/plans/2026-08-01-judgment-capability-spike.md` (verbatim)
- Design: flattener MUST reuse filter_events_in_window and filter_events_to_anchor_host — do not reimplement

## Allowed files

- evals/capability/bundle.py
- tests/evals/capability/test_bundle.py
- .workflow/capability-spike-03-bundle/

## Do not touch

src/praetor/**, evals/harness.py, evals/scenarios/**, agentic judgment

## Instructions

1. TDD Task 3 from plan exactly.
2. Verify commands green.
3. Do not mark queue done; no phase exit.
4. Commit: `Add Path B bundle builder reusing correlation window and host filters.`

Write `results/implementer-result.md`.
