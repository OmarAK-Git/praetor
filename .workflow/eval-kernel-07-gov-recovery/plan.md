# eval-kernel-07-gov-recovery

**Goal:** Task 7 — gov.recovery_never_contains: engine recovery of a non-terminal attempt never emits auto_contain.

**Scope:** This governance pin only. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass on FakeProvider.
- Recovery never emits auto_contain.
- Pin uses run_engine_startup_recovery / recovery resolver, not a PolicyGate-only shortcut.
- The verifier checks only Task 7 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/gov.recovery_never_contains.yaml
- tests/evals/e2e/test_gov_recovery_never_contains.py
- .workflow/eval-kernel-07-gov-recovery/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_gov_recovery_never_contains.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_recovery_never_contains.py
- mypy evals/e2e_kernel.py
