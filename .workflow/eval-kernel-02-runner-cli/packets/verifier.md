# Verifier packet — eval-kernel-02-runner-cli

Treat implementer claims as unevidenced until you re-run commands.
Ignore phase/sprint gaps. scope=task.

## Goal

Task 2 — e2e_kernel runner skeleton + harness CLI.

## Acceptance criteria

- python -m evals.harness with no args still runs only the Outcome Matrix suite.
- --e2e and --all are recognized on the same CLI.
- REQUIRED_E2E_SCENARIO_IDS lists the locked 15 IDs.
- evals.e2e_kernel does not import evals.capability.flatten.
- The verifier checks only Task 2 acceptance, not Sprint 1 gate completion.

## Changed files

- evals/e2e_kernel.py
- evals/e2e_scenarios/.gitkeep
- evals/harness.py
- tests/evals/test_e2e_kernel.py

## Commands (run yourself)

- pytest tests/evals/test_e2e_kernel.py tests/evals/test_eval_harness.py -q
- ruff check evals/e2e_kernel.py evals/harness.py tests/evals/test_e2e_kernel.py
- mypy evals/e2e_kernel.py evals/harness.py

## Manual checks

- Default no-arg harness path unchanged.
- No Path B import on the kernel module.

## Implementer result (unevidenced)

.workflow/eval-kernel-02-runner-cli/results/implementer-result.md

Write .workflow/eval-kernel-02-runner-cli/results/verifier-result.md
Outcome: pass | gaps | human_needed
