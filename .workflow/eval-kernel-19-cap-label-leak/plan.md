# eval-kernel-19-cap-label-leak

**Goal:** Task 19 — cap.no_label_leak_ids: ground-truth labels, seed EventRecordIDs, and expected_class do not appear in provider-visible excerpts or alert_identity; both arms pass.

**Scope:** This theater pin only. Do not mark it pending. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass when IDs do not leak (no pending).
- Leak of labels, seed EventRecordIDs, or expected_class is failure_class=theater_detector.
- All 15 required scenario IDs now exist on disk.
- The verifier checks only Task 19 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/theater.py
- evals/e2e_scenarios/cap.no_label_leak_ids.yaml
- tests/evals/e2e/test_cap_no_label_leak_ids.py
- tests/evals/test_e2e_kernel.py
- .workflow/eval-kernel-19-cap-label-leak/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_cap_no_label_leak_ids.py tests/evals/test_e2e_kernel.py::test_required_ids_are_the_locked_fifteen tests/evals/test_e2e_kernel.py::test_full_suite_has_thirty_rows_and_exits_zero -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_cap_no_label_leak_ids.py tests/evals/test_e2e_kernel.py
- mypy evals/e2e_kernel.py
