# eval-kernel-09-des-path-b

**Goal:** Task 9 — des.path_b_stays_out_of_src: AST/import guard that src/praetor does not import Path B flatteners.

**Scope:** This design pin only. Do not promote Path B. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass.
- src/praetor import of evals.capability.flatten or a Path B flattener is a theater_detector fail.
- Path B remains under evals/.
- The verifier checks only Task 9 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/des.path_b_stays_out_of_src.yaml
- tests/evals/e2e/test_des_path_b_stays_out_of_src.py
- .workflow/eval-kernel-09-des-path-b/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_des_path_b_stays_out_of_src.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_path_b_stays_out_of_src.py
- mypy evals/e2e_kernel.py
