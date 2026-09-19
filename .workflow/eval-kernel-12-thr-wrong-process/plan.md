# eval-kernel-12-thr-wrong-process

**Goal:** Task 12 — thr.valid_cite_wrong_process: valid citations that omit the subject Path A fact are recorded as a cite-to-subject miss; authority must not treat valid cite as right subject.

**Scope:** Record the miss only. Do not implement Sprint 2 McNemar. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass the Sprint 1 authority pin.
- Citations resolve but omit the subject Path A fact; that miss is recorded.
- No cite-to-subject McNemar or Sprint 2 primary scoring is implemented.
- The verifier checks only Task 12 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/thr.valid_cite_wrong_process.yaml
- tests/evals/e2e/test_thr_valid_cite_wrong_process.py
- .workflow/eval-kernel-12-thr-wrong-process/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_thr_valid_cite_wrong_process.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_thr_valid_cite_wrong_process.py
- mypy evals/e2e_kernel.py
