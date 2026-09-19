# eval-kernel-18-cap-stump

**Goal:** Task 18 — cap.stump_parity_guard: compute path_a_fact_count stump and emit McNemar-ready pairs; do not pass this as judgment beats stump; new_build pending.

**Scope:** Stump helper plus this capability pin only. Do not claim a quality win. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- path_a_fact_count_stump and stump_pair exist and are McNemar-ready.
- new_build is pending, not pass; no quality-win assertion.
- old_build is recorded honestly (new≈stump or pending new).
- The verifier checks only Task 18 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/stump.py
- evals/e2e_kernel.py
- evals/e2e_scenarios/cap.stump_parity_guard.yaml
- tests/evals/test_stump.py
- tests/evals/e2e/test_cap_stump_parity_guard.py
- .workflow/eval-kernel-18-cap-stump/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/test_stump.py tests/evals/e2e/test_cap_stump_parity_guard.py -q
- ruff check evals/stump.py evals/e2e_kernel.py tests/evals/test_stump.py tests/evals/e2e/test_cap_stump_parity_guard.py
- mypy evals/stump.py evals/e2e_kernel.py
