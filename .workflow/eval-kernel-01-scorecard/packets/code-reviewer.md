# Code review packet — eval-kernel-01-scorecard

Review Task 1 only. Ignore Sprint 1 gate gaps.

## Goal

Scorecard schema + Pydantic model with honesty rules.

## Changed files

- evals/schemas/scorecard_schema.json
- evals/scorecard.py
- tests/evals/test_scorecard.py

## Plan / spec

- docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md Task 1
- docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md §4

## Check

Spec compliance, extra=forbid, pending legality, failure_class rules, no writes outside files_allowed, no src/praetor or harness edits.

Write findings to .workflow/eval-kernel-01-scorecard/results/code-review.md
Verdict: approve | request_changes (blocking) | comment
