# eval-kernel-14-use-ledger

**Goal:** Task 14 — use.reconstruct_from_ledger: after completed intake, ledger rows plus decision_id / evidence_bundle_hash reconstruct the asserted edict fields.

**Scope:** This usability pin only. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass.
- Ledger reconstruction matches the scorecard-asserted edict fields.
- Inability to rebuild the story is failure_class=harness.
- The verifier checks only Task 14 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/use.reconstruct_from_ledger.yaml
- tests/evals/e2e/test_use_reconstruct_from_ledger.py
- .workflow/eval-kernel-14-use-ledger/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_use_reconstruct_from_ledger.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_reconstruct_from_ledger.py
- mypy evals/e2e_kernel.py
