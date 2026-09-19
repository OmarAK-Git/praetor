# Verifier packet — eval-kernel-03-scenario-loader

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 3 — E2E scenario YAML contract loader.

## Acceptance criteria
- E2E YAML lives under evals/e2e_scenarios or a tests fixture tree, not evals/scenarios.
- load_e2e_scenario rejects stem/id mismatch, missing theater_detector, and skip flags.
- Required spec §4 fields are enforced.
- The verifier checks only Task 3 acceptance, not Sprint 1 gate completion.

## Changed files
- evals/schemas/e2e_scenario_schema.json
- evals/e2e_scenario.py
- tests/evals/test_e2e_scenario.py
- tests/evals/fixtures/e2e/

## Commands
- pytest tests/evals/test_e2e_scenario.py -q
- ruff check evals/e2e_scenario.py tests/evals/test_e2e_scenario.py
- mypy evals/e2e_scenario.py

## Manual checks
- Outcome Matrix scenario_schema.json is untouched.
- No CBC JSON or extra envelope fields in the loader contract.

## Implementer result (unevidenced)
.workflow/eval-kernel-03-scenario-loader/results/implementer-result.md

Write .workflow/eval-kernel-03-scenario-loader/results/verifier-result.md
Outcome: pass | gaps | human_needed
