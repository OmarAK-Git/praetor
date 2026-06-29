# Verification Ledger — V2-004

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | DEC-061 + §13 | `rg "DEC-061" docs/decisions.md` + §13 read | Row documented | §13 row + DEC-061 section | pass |
| VERIFY-002 | REQ-002 | Enum + SFE | `OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE` + `OUTCOME_MATRIX_SFE` | SFE true | `True` | pass |
| VERIFY-003 | REQ-003 | LLM flags | `PROVIDER_UNAVAILABLE in LLM_FAILURE_FAULT_FLAGS` | present | present | pass |
| VERIFY-004 | REQ-004 | Completeness guard | `pytest tests/evals/test_eval_harness.py -q` | pass | pass | pass |
| VERIFY-005 | REQ-005 | Intake mapping | `pytest tests/judgment/test_provider_failures.py -q -k unavailable` | pass | 1 passed | pass |
| VERIFY-006 | REQ-006 | Breaker independence | `pytest tests/judgment/test_provider_health_breaker.py -q -k unavailable` | pass | 1 passed | pass |
| VERIFY-007 | No regression | Default pytest gate | `python -m pytest -q` | pass | **785 passed**, 2 deselected, 1 xfailed | pass |
| VERIFY-008 | Backlog | delivery_backlog | `rg "DEC-061" docs/proposals/delivery_backlog.md` | P1 row resolved | Resolved (DEC-061, V2-004) | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Full `mypy src` | Small typed surface; no new type errors observed in pytest | Low |

## Verification run (2026-06-29)

```
python -m pytest -q
pytest tests/evals/test_eval_harness.py -q
pytest tests/judgment/test_provider_failures.py -q -k unavailable
pytest tests/judgment/test_provider_health_breaker.py -q -k unavailable
rg "DEC-061" docs/
```
