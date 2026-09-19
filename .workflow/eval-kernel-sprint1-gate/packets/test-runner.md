# Test-runner packet — eval-kernel-sprint1-gate

Verify-only. Do not implement. Do not edit src/ or tests/.

Run these commands from C:\Users\oalan\Praetor and record exit codes + summaries:

1. pytest -q
2. ruff check src tests evals consumer_sdk
3. mypy src evals consumer_sdk
4. python -m evals.harness
5. python -m evals.harness --all

Write .workflow/eval-kernel-sprint1-gate/results/test-runner-result.md with each command, exit code, and a short summary (pass counts, pending rows, any failures).
