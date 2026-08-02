# Implementer packet — capability-spike-04-runner

## Objective

Add Observation record and two-path runner for Path A (correlate_telemetry) and Path B (evidence_bundle).

## Docs

- Plan **Task 4** in `docs/superpowers/plans/2026-08-01-judgment-capability-spike.md` (verbatim tests + implementation)
- Note: ModelJudgment via `result.edict.model_judgment`; guard when edict is None

## Allowed files

- evals/capability/runner.py
- tests/evals/capability/test_runner.py
- .workflow/capability-spike-04-runner/

## Do not touch

src/praetor/**, evals/harness.py, evals/scenarios/**, praetor.judgment.agentic

## Instructions

1. TDD Task 4 from plan exactly; FakeProvider only.
2. Verify commands green.
3. Do not mark queue done; no phase exit.
4. Commit: `Add two-path anchor runner recording model judgment and gate outcome.`

Write `results/implementer-result.md`.
