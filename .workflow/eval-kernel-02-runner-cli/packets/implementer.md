# Implementer packet — eval-kernel-02-runner-cli

## Objective

Task 2 — e2e_kernel runner skeleton + harness CLI.

## Original user goal

Drain accepted eval-kernel Sprint 1. This is Task 2.

## Relevant docs

- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` — **Task 2** (follow steps/tests/code verbatim)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §4 harness architecture

## Allowed files (write only these)

- evals/e2e_kernel.py
- evals/e2e_scenarios/.gitkeep
- evals/harness.py
- tests/evals/test_e2e_kernel.py
- .workflow/eval-kernel-02-runner-cli/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

## Do not touch

- `src/praetor/**`
- Outcome Matrix scenario YAML / stipulated-disposition runner contracts
- Path B (`evals.capability.flatten`)
- Any file outside files_allowed

## Acceptance criteria

- python -m evals.harness with no args still runs only the Outcome Matrix suite.
- --e2e and --all are recognized on the same CLI.
- REQUIRED_E2E_SCENARIO_IDS lists the locked 15 IDs.
- evals.e2e_kernel does not import evals.capability.flatten.
- The verifier checks only Task 2 acceptance, not Sprint 1 gate completion.

## Implementation instructions

1. Implement Task 2 from the plan exactly (TDD).
2. Default no-arg `python -m evals.harness` must stay Outcome Matrix only.
3. Empty e2e_scenarios directory must emit harness error rows for missing IDs.
4. Do not mark the queue item done. Do not run the Sprint 1 gate.
5. Stop and report approval_gates before dependency installs or writes outside files_allowed.
6. Commit with the plan commit message if specified; otherwise a concise feat(evals) message. Push the current branch.

## Verification commands

- pytest tests/evals/test_e2e_kernel.py tests/evals/test_eval_harness.py -q
- ruff check evals/e2e_kernel.py evals/harness.py tests/evals/test_e2e_kernel.py
- mypy evals/e2e_kernel.py evals/harness.py

## Expected result schema

Write `.workflow/eval-kernel-02-runner-cli/results/implementer-result.md` with files, commands/exit codes, commit SHA, status.
