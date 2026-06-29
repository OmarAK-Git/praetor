# Final Report — V2-004

## Summary

Ratified **DEC-061** and wired **`provider_unavailable`** as the canonical Outcome Matrix fault flag for `ProviderUnavailableError`: `escalate` with `system_fault_escalation=true`. Enum, `evals/outcome_matrix.py`, `LLM_FAILURE_FAULT_FLAGS`, harness scenario, `FakeProviderMode.UNAVAILABLE`, and minimal `process_alert_intake` catch land in this task. Provider-health breaker tripping on `ProviderUnavailableError` is unchanged.

**V2 Gate 0 is closed** (V2-001 – V2-004).

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 §13 row | `docs/contracts.md` §13 after `provider_refusal` |
| REQ-002 Enum + SFE | `OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE`; `OUTCOME_MATRIX_SFE` |
| REQ-003 LLM flags | `LLM_FAILURE_FAULT_FLAGS` includes `PROVIDER_UNAVAILABLE` |
| REQ-004 Harness | `evals/scenarios/provider_unavailable.yaml`; completeness guard green |
| REQ-005 Intake catch | `orchestrator.py` except `ProviderUnavailableError` |
| REQ-006 Breaker independence | `test_provider_unavailable_trips_breaker` unchanged pass |

## Files changed

- `docs/contracts.md` — §13 `provider_unavailable` row
- `docs/decisions.md` — DEC-061 table row + section
- `docs/proposals/delivery_backlog.md` — P1 ProviderUnavailable row resolved
- `src/praetor/metrics/events.py` — enum + `LLM_FAILURE_FAULT_FLAGS`
- `evals/outcome_matrix.py` — SFE polarity
- `src/praetor/judgment/fake_provider.py` — `UNAVAILABLE` mode
- `src/praetor/engine/orchestrator.py` — intake catch
- `evals/scenarios/provider_unavailable.yaml` — harness scenario
- `tests/evals/test_provider_unavailable_matrix.py` — matrix alignment (3 tests)
- `tests/judgment/test_provider_failures.py` — `test_provider_unavailable_escalates`
- `memory-bank/{tasks,activeContext,progress,decisions}.md`
- `.workflow/V2-004/{plan,state,traceability,verification,review,final-report}.md`

## Verification performed

```
python -m pytest -q
```

| Check | Result |
|---|---|
| pytest | **785 passed**, 2 deselected, 1 xfailed |
| DEC-061 grep | hits in `decisions.md`, `delivery_backlog.md` |
| §13 row | `provider_unavailable` with SFE=true |

## Known gaps

- V2-007 owns fuller intake/metrics/breaker test coverage and operator doc reconciliation.
- V2-016 static fault-flag guard not yet enforcing enum subset on `DecisionEdict` construction.
- `docs/spec.md` mirror deferred until spec unfreeze.

## safe_to_commit

yes — 2026-06-29 verification green
