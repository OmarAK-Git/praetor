# Implementer packet — eval-kernel-03-scenario-loader

## Objective

Task 3 — E2E scenario YAML contract loader.

## Relevant docs

- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` — **Task 3** (follow verbatim)
- Spec §4 scenario contract

## Allowed files

- evals/schemas/e2e_scenario_schema.json
- evals/e2e_scenario.py
- tests/evals/test_e2e_scenario.py
- tests/evals/fixtures/e2e/
- .workflow/eval-kernel-03-scenario-loader/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

## Do not touch

- evals/scenarios/**
- evals/schemas/scenario_schema.json
- src/praetor/**
- Any file outside files_allowed

## Acceptance criteria

- E2E YAML lives under evals/e2e_scenarios or a tests fixture tree, not evals/scenarios.
- load_e2e_scenario rejects stem/id mismatch, missing theater_detector, and skip flags.
- Required spec §4 fields are enforced.
- The verifier checks only Task 3 acceptance, not Sprint 1 gate completion.

## Instructions

Implement Task 3 from the plan exactly (TDD). Do not execute scenarios. Do not mark queue done. Commit and push if clean.

Write `.workflow/eval-kernel-03-scenario-loader/results/implementer-result.md`.
