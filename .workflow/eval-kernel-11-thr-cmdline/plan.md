# eval-kernel-11-thr-cmdline

**Goal:** Task 11 — thr.instruction_in_cmdline: instruction-like command_line text survives excerpting and is not a FakeProvider do-what-I-say win.

**Scope:** This threat pin only. Live-model half stays opt-in. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass on the deterministic FakeProvider half.
- Instruction-like command_line survives excerpting.
- No silent skip of a live-model half if present.
- The verifier checks only Task 11 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/thr.instruction_in_cmdline.yaml
- tests/evals/e2e/test_thr_instruction_in_cmdline.py
- .workflow/eval-kernel-11-thr-cmdline/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_thr_instruction_in_cmdline.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_thr_instruction_in_cmdline.py
- mypy evals/e2e_kernel.py
