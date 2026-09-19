# eval-kernel-21-docs-pointer

**Goal:** Task 21 — Docs pointer: eval_gates and memory-bank point at the Sprint 1 plan; CBC queue-item retire stays deferred to Sprint 3.

**Scope:** Pointer docs only. Do not retire CBC items. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- docs/eval_gates.md points at the Sprint 1 plan and the new workflow.
- memory-bank current-focus / next-up point here instead of CBC AlertEnvelope spike as the next authorized step.
- CBC queue items are not fully retired (Sprint 3).
- The verifier checks only Task 21 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- docs/eval_gates.md
- memory-bank/activeContext.md
- memory-bank/tasks.md
- memory-bank/progress.md
- tests/docs/test_eval_kernel_pointer.py
- .workflow/eval-kernel-21-docs-pointer/

**Verification commands:**

- pytest tests/docs/test_eval_kernel_pointer.py -q
