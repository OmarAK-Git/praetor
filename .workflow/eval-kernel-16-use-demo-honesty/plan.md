# eval-kernel-16-use-demo-honesty

**Goal:** Task 16 — use.demo_honesty_gate: demo/walkthrough/kernel copy must not claim judgment works while the Sprint 2 cite-to-subject primary is unearned.

**Scope:** This usability pin only. Do not claim capability. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass when demo copy does not claim unearned judgment.
- Unearned capability claims trip theater_detector unearned_demo_claim.
- A stump-only win is not treated as a claim.
- The verifier checks only Task 16 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/use.demo_honesty_gate.yaml
- tests/evals/e2e/test_use_demo_honesty_gate.py
- .workflow/eval-kernel-16-use-demo-honesty/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_use_demo_honesty_gate.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_demo_honesty_gate.py
- mypy evals/e2e_kernel.py
