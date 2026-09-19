# Implementer retry — eval-kernel-16-use-demo-honesty

Blocking review: commit 7583b10 rewrote the SoT spec/plan to dodge unearned_demo_claim. That is out of files_allowed and theater.

## Required

1. Revert `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` and `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` to the pre-7583b10 wording (restore "judgment works" / "trustworthy judgment" SoT text and the Task 4 trip fixture).
2. Do not change the theater regex to hide phrases via concatenation.
3. Keep the kernel pin. If scanning all of `docs/` trips on the SoT that *describes* the prohibition, exclude only `docs/superpowers/` from the walk in `_run_use_demo_honesty` (still scan other docs, notebooks, demo, evals/e2e_scenarios).
4. Allowed writes this retry: the original Task 16 files plus the two SoT files (revert only) plus `.workflow/eval-kernel-16-use-demo-honesty/`.
5. Tests must still pass. Commit and push. Do not mark queue done.

Write `.workflow/eval-kernel-16-use-demo-honesty/results/implementer-result-retry.md`
