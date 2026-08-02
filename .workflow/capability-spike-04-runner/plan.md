# capability-spike-04-runner

## Goal

Add Observation record and two-path runner that exercises process_alert_intake for Path A (correlate) and Path B (bundle).

## Scope

evals/capability/runner.py + unit tests with FakeProvider only.

## Allowed files

- evals/capability/runner.py
- tests/evals/capability/test_runner.py
- .workflow/capability-spike-04-runner/

## Acceptance criteria

- run_anchor produces Observations for PATH_A and PATH_B.
- proposed_disposition read from result.edict.model_judgment when present.
- final_disposition/fault_flags recorded but not scored here.
- Offline FakeProvider tests pass with no API key.

## Verification

- `pytest tests/evals/capability/test_runner.py -q`
- `ruff check evals/capability/runner.py tests/evals/capability/test_runner.py`
- `mypy evals/capability/runner.py`
