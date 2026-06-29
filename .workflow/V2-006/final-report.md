# Final Report — V2-006

## Summary

Implemented **DEC-058 rule-action semantics (V2-006)**: sole matching `escalate` or `deny` rules block `auto_contain` at the policy layer with distinct fault flags (`containment_policy_escalation_required`, `containment_policy_denied`); unresolved permit+block conflicts still emit `policy_ambiguity`. Example org catch-all `escalate` now correctly blocks containment.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 Sole escalate blocks containment | `test_sole_escalate_rule_blocks_containment`, `test_sole_escalate_rule_blocks_auto_contain` |
| REQ-002 Deny vs escalate distinct results | `test_deny_and_escalate_distinct_results`, gate deny/escalate tests |
| REQ-003 Conflict → policy_ambiguity | `test_target_scoped_policy_conflict_is_ambiguous`, `test_policy_ambiguity_escalates` |
| REQ-004 Gate maps distinct fault flags | gate integration tests + eval scenarios |

## Files changed

**Production**
- `src/praetor/policy/containment_policy.py` — `PolicyAction.ESCALATE`, blocking logic, fault flag constants
- `src/praetor/policy/gate.py` — distinct deny/escalate escalate paths
- `src/praetor/metrics/events.py` — new `OutcomeMatrixFaultFlag` members
- `evals/outcome_matrix.py` — SFE polarity for new flags
- `evals/harness.py` — permissive policy for auto_contain scenarios; deny/escalate scenario preconditions
- `evals/run_phase3_gate.py` — permissive host gate check

**Tests / scenarios**
- `tests/policy/test_containment_policy.py`, `test_policy_gate.py`, `conftest.py`
- `evals/scenarios/containment_policy_denied.yaml`, `containment_policy_escalation_required.yaml`
- Integration test updates (benchmarks, correlation, containment, engine, metrics, citation targeting, directive hash)

**Workflow / memory bank**
- `.workflow/V2-006/*`, `memory-bank/{tasks,activeContext,progress}.md`

## Verification (VS-0001, 2026-06-29)

```
python -m pytest -q
python -m mypy src evals consumer_sdk
python -m ruff check src tests evals consumer_sdk
```

| Check | Result |
|---|---|
| pytest | **799 passed**, 2 deselected, 1 xfailed |
| mypy | 118 source files, no issues |
| ruff | All checks passed |

## Known gaps

- No-rule implicit ALLOW fallthrough deferred to **V2-013**.
- `default_action` schema/preflight deferred to **V2-012**.
- `docs/contracts.md` §13 rows for new fault flags deferred (task constraint; names provisional per DEC-058).

## safe_to_commit

yes — VS-0001 full gate green (2026-06-29)
