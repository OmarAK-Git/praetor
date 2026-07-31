# corroboration-floor-03-gate-harness

## Goal
Retarget insufficient_corroboration harness and PolicyGate/engine tests to sole-ambiguous / zero-anchor failures under the temporary floor.

## Scope
Harness scenario + policy/engine/correlation tests that assert old >=2 semantics.

## Acceptance criteria
- Harness insufficient_corroboration covers OM row via sole ambiguous host citation (escalate, flag, SFE=false).
- Single-provenance host auto_contain no longer escalates solely for insufficient_corroboration.
- Touched policy/engine/eval/correlation tests updated and green.

## Files allowed
- evals/scenarios/insufficient_corroboration.yaml
- tests/policy/
- tests/engine/test_gate_target_ownership.py
- tests/evals/
- tests/correlation/
- .workflow/corroboration-floor-03-gate-harness/

## Verification
- pytest tests/policy/test_host_corroboration_gate.py tests/policy/test_policy_gate.py tests/engine/test_gate_target_ownership.py tests/evals/test_eval_harness.py -q
- ruff check tests/policy tests/engine/test_gate_target_ownership.py

## Tier
T2
