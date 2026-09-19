# eval-kernel-03-scenario-loader

**Goal:** Task 3 — E2E scenario YAML contract loader: sibling-tree schema, filename stem must match scenario_id, no skip flags, theater_detector required.

**Scope:** E2E YAML schema and loader only. Do not execute scenarios. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- E2E YAML lives under evals/e2e_scenarios or a tests fixture tree, not evals/scenarios.
- load_e2e_scenario rejects stem/id mismatch, missing theater_detector, and skip flags.
- Required spec §4 fields are enforced.
- The verifier checks only Task 3 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/schemas/e2e_scenario_schema.json
- evals/e2e_scenario.py
- tests/evals/test_e2e_scenario.py
- tests/evals/fixtures/e2e/
- .workflow/eval-kernel-03-scenario-loader/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/test_e2e_scenario.py -q
- ruff check evals/e2e_scenario.py tests/evals/test_e2e_scenario.py
- mypy evals/e2e_scenario.py
