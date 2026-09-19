# Implementer packet — eval-kernel-19-cap-label-leak

Implement Task 19 from docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md exactly (### Task 19 through commit, before Task 20).

Both arms pass (not pending). This ID is NOT in CAPABILITY_QUALITY_IDS. Do not force pending.

Also:
- Replace test_harness_e2e_flag_exits_nonzero_on_empty_kernel in tests/evals/test_e2e_kernel.py (keep the empty-directory unit test).
- Add test_full_suite_has_thirty_rows_and_exits_zero.
- After this task, run_e2e_kernel() against real evals/e2e_scenarios/ must emit 30 rows and kernel_exit_code 0.

Only files_allowed (includes tests/evals/test_e2e_kernel.py per the plan). TDD. Commit and push. Do not mark queue done.

Write .workflow/eval-kernel-19-cap-label-leak/results/implementer-result.md
