# Gate test-runner packet — capability-spike-gate

Run these commands from repo root C:\Users\oalan\Praetor and capture full exit codes + key summary lines:

1. `pytest -q`
2. `ruff check src tests evals consumer_sdk`
3. `mypy src evals consumer_sdk`
4. `python -m evals.harness`
5. `python -m evals.capability_spike`

Also check:
- All six task verifier results exist and say PASS:
  - `.workflow/capability-spike-01-corpus/results/verifier-result.md`
  - `.workflow/capability-spike-02-flatten/results/verifier-result.md`
  - `.workflow/capability-spike-03-bundle/results/verifier-result.md`
  - `.workflow/capability-spike-04-runner/results/verifier-result.md`
  - `.workflow/capability-spike-05-score/results/verifier-result.md`
  - `.workflow/capability-spike-06-cli/results/verifier-result.md`
- `git log --oneline --name-only` for capability-spike commits: confirm no src/praetor or evals/harness.py or evals/scenarios changes in those commits (1891684, 41eae19, 9cb454a, 37083e0, 82b41ad, 98debe4, 2450e66)

If pytest fails only on `tests/runtime/test_startup_guard.py::TestSingletonLock::test_two_subprocesses_race_only_one_wins`, re-run that test alone once and note flake status.

Write `.workflow/capability-spike-gate/results/test-runner-result.md` with all command outputs/exit codes.

Return a concise summary of pass/fail per command.
