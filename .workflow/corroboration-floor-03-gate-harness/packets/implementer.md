# Implementer packet — corroboration-floor-03-gate-harness

## Objective
Retarget harness + policy/engine/eval/correlation tests for DEC-065 temporary floor.

## Locked behavior
- Single provenance host citation may authorize (no longer insufficient_corroboration by itself).
- insufficient_corroboration harness must use sole ambiguous host citation (or zero anchors if the harness runner can express that).
- Account tests that required sysmon+security pair must accept ≥1 fact.

## Allowed files
- evals/scenarios/insufficient_corroboration.yaml
- tests/policy/
- tests/engine/test_gate_target_ownership.py
- tests/evals/
- tests/correlation/
- .workflow/corroboration-floor-03-gate-harness/

## Do not touch
- src/praetor/evidence/provenance.py (done in task 02)
- docs (done in task 01)
- Do NOT commit

## Verification
- pytest tests/policy/test_host_corroboration_gate.py tests/policy/test_policy_gate.py tests/engine/test_gate_target_ownership.py tests/evals/test_eval_harness.py -q
- Also run any correlation tests you change.
- ruff check tests/policy tests/engine/test_gate_target_ownership.py

Write `.workflow/corroboration-floor-03-gate-harness/results/implementer-result.md`.
