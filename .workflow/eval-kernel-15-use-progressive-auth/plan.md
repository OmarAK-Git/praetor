# eval-kernel-15-use-progressive-auth

**Goal:** Task 15 — use.progressive_auth_report: build_progressive_authorization_report reads evaluation rows written by the same intake; report is read-only.

**Scope:** This usability pin only. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass.
- Report reads evaluation rows from the same intake and is read-only.
- A missing evaluation row is a harness fail.
- The verifier checks only Task 15 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/use.progressive_auth_report.yaml
- tests/evals/e2e/test_use_progressive_auth_report.py
- .workflow/eval-kernel-15-use-progressive-auth/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_use_progressive_auth_report.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_progressive_auth_report.py
- mypy evals/e2e_kernel.py
