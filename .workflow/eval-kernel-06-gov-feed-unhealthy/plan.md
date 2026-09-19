# eval-kernel-06-gov-feed-unhealthy

**Goal:** Task 6 — gov.feed_unhealthy_blocks_contain: unhealthy revocation feed blocks auto_contain and still allows standard_review via production intake.

**Scope:** This governance pin only. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass on FakeProvider.
- Unhealthy feed blocks auto_contain and allows standard_review.
- Uses the same degraded-mode contract as the playbook fixture.
- The verifier checks only Task 6 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/gov.feed_unhealthy_blocks_contain.yaml
- tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py
- .workflow/eval-kernel-06-gov-feed-unhealthy/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py
- mypy evals/e2e_kernel.py
