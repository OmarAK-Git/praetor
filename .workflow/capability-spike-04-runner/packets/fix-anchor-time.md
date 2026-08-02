# Fix packet — capability-spike-04-runner

## Blocking finding

Path A calls `process_alert_intake` without `anchor_time`, so orchestrator uses `datetime.now(UTC)` and historical fixture events fall outside the ±300s window → empty correlation → FakeProvider never runs.

## Required fix

1. In `evals/capability/runner.py`, pass `anchor_time=anchor.anchor_time` in `intake_kwargs` for every intake call (both paths; required for Path A).
2. In `tests/evals/capability/test_runner.py`, add a test that Path A observations with in-window events do **not** carry `correlation_failure` and that `proposed_disposition` matches the FakeProvider disposition (proves provider was consulted).
3. Re-run verification commands; commit fix.

## Allowed files

- evals/capability/runner.py
- tests/evals/capability/test_runner.py
- .workflow/capability-spike-04-runner/

## Commit message

`Fix Path A spike runner to pass anchor_time into intake.`

Do not mark queue done. Write `results/implementer-result-fix.md`.
