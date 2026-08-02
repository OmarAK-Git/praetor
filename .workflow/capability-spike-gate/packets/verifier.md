# Gate verifier packet — capability-spike-gate

## Goal

Verify judgment capability spike sprint with repository-wide test, lint, typecheck, and mandatory harness gates.

## Acceptance criteria

- Full pytest suite passes (startup_guard race flake: re-run alone if needed).
- Repository-wide ruff and mypy pass on src/tests/evals/consumer_sdk.
- python -m evals.harness still reports mandatory scenarios green (count may be 34 after enrichment-split; must not regress).
- python -m evals.capability_spike exits 0 skipped offline.
- All six task verifier artifacts exist and PASS.
- No src/praetor/ changes from this sprint; harness/scenarios untouched.

## Evidence from test-runner

`.workflow/capability-spike-gate/results/test-runner-result.md`

## Manual checks

- Confirm measurement-only: no production code changes for this spike.
- Confirm agentic judgment path was not imported.
- Confirm gating suite is still offline/network-free.

## Instructions

Treat test-runner claims as unevidenced until spot-checked. You may re-run critical commands. This is phase_exit scope.

Write `.workflow/capability-spike-gate/results/verifier-result.md` with PASS/FAIL.
