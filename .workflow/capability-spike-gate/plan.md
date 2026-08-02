# capability-spike-gate

## Goal

Verify judgment capability spike sprint with repository-wide test, lint, typecheck, and mandatory harness gates.

## Scope

Verify-only final plan gate; no feature implementation.

## Acceptance criteria

- Full pytest suite passes (startup_guard race flake: re-run alone if needed).
- Repository-wide ruff and mypy pass on src/tests/evals/consumer_sdk.
- python -m evals.harness still reports 33 scenarios green.
- python -m evals.capability_spike exits 0 skipped offline.
- All six task verifier artifacts exist and PASS.
- No src/praetor/ changes from this sprint; harness/scenarios untouched.

## Verification commands

- `pytest -q`
- `ruff check src tests evals consumer_sdk`
- `mypy src evals consumer_sdk`
- `python -m evals.harness`
- `python -m evals.capability_spike`
