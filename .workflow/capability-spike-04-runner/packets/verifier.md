# Verifier packet — capability-spike-04-runner

## Goal

Add Observation record and two-path runner that exercises process_alert_intake for Path A (correlate) and Path B (bundle).

## Acceptance criteria

- run_anchor produces Observations for PATH_A and PATH_B.
- proposed_disposition read from result.edict.model_judgment when present.
- final_disposition/fault_flags recorded but not scored here.
- Offline FakeProvider tests pass with no API key.

## Changed files (commit 37083e0)

- evals/capability/runner.py
- tests/evals/capability/test_runner.py

## Commands

- `pytest tests/evals/capability/test_runner.py -q`
- `ruff check evals/capability/runner.py tests/evals/capability/test_runner.py`
- `mypy evals/capability/runner.py`

## Manual

- Never imports praetor.judgment.agentic.
- Uses single-shot GenAI wrapper path only.
- No src/praetor/ edits; no evals/harness.py edits.

Implementer: `.workflow/capability-spike-04-runner/results/implementer-result.md`
Task scope. Write `results/verifier-result.md`.
