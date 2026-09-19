# Verifier packet — eval-kernel-19-cap-label-leak

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 19 — cap.no_label_leak_ids.

## Acceptance criteria
- Both arms pass when IDs do not leak (no pending).
- Leak of labels, seed EventRecordIDs, or expected_class is failure_class=theater_detector.
- All 15 required scenario IDs now exist on disk.
- The verifier checks only Task 19 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_cap_no_label_leak_ids.py tests/evals/test_e2e_kernel.py::test_required_ids_are_the_locked_fifteen tests/evals/test_e2e_kernel.py::test_full_suite_has_thirty_rows_and_exits_zero -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_cap_no_label_leak_ids.py tests/evals/test_e2e_kernel.py
- mypy evals/e2e_kernel.py

Write .workflow/eval-kernel-19-cap-label-leak/results/verifier-result.md
Outcome: pass | gaps | human_needed
