# eval-kernel-02-runner-cli

**Goal:** Task 2 — e2e_kernel runner skeleton + harness CLI: thin sibling imported by evals.harness; --e2e/--all flags; default no-arg path stays Outcome Matrix only; no Path B import.

**Scope:** Kernel skeleton and harness CLI wiring only. Do not add scenario YAML or executors. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- python -m evals.harness with no args still runs only the Outcome Matrix suite.
- --e2e and --all are recognized on the same CLI.
- REQUIRED_E2E_SCENARIO_IDS lists the locked 15 IDs.
- evals.e2e_kernel does not import evals.capability.flatten.
- The verifier checks only Task 2 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/.gitkeep
- evals/harness.py
- tests/evals/test_e2e_kernel.py
- .workflow/eval-kernel-02-runner-cli/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/test_e2e_kernel.py tests/evals/test_eval_harness.py -q
- ruff check evals/e2e_kernel.py evals/harness.py tests/evals/test_e2e_kernel.py
- mypy evals/e2e_kernel.py evals/harness.py
