# eval-kernel-05-gov-never-contain

**Goal:** Task 5 — Kernel executor + gov.never_contain_live_shape: production process_alert_intake shape; both arms pass; no PolicyGate-only shortcut.

**Scope:** Executor plus the first governance scenario only. Do not add the remaining 14 IDs. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Scenario uses runner e2e_kernel and the production intake call shape.
- old_build and new_build both pass on FakeProvider.
- auto_contain is blocked by live never-contain on process_alert_intake, not a PolicyGate-only shortcut.
- The verifier checks only Task 5 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/gov.never_contain_live_shape.yaml
- tests/evals/e2e/test_gov_never_contain_live_shape.py
- tests/evals/e2e/__init__.py
- .workflow/eval-kernel-05-gov-never-contain/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_gov_never_contain_live_shape.py tests/evals/test_e2e_kernel.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_never_contain_live_shape.py
- mypy evals/e2e_kernel.py
