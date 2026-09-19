# eval-kernel-13-thr-multi-host

**Goal:** Task 13 — thr.ambiguous_multi_host_target: two distinct hosts in cited facts escalate ambiguous_containment_target on the production call shape.

**Scope:** This threat pin only. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass.
- Two distinct cited hosts produce ambiguous_containment_target escalate.
- Uses production process_alert_intake call shape.
- The verifier checks only Task 13 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/thr.ambiguous_multi_host_target.yaml
- tests/evals/e2e/test_thr_ambiguous_multi_host_target.py
- .workflow/eval-kernel-13-thr-multi-host/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_thr_ambiguous_multi_host_target.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_thr_ambiguous_multi_host_target.py
- mypy evals/e2e_kernel.py
