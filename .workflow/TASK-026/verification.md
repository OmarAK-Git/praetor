# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | Matrix completeness | Escalate-row guard | `test_outcome_matrix_completeness_guard` | 17 pairs | 17 covered | pass |
| VERIFY-002 | Canonical enum | Fault flag enum test | `test_scenario_fault_flags_are_canonical_enum_values` | pass | pass | pass |
| VERIFY-003 | SFE polarity | Canonical map test | `test_scenario_sfe_polarity_matches_canonical_map` | pass | pass | pass |
| VERIFY-004 | ticket_stamp_failed | Dedicated scenario | `test_ticket_stamp_failed_scenario_present` | pass | pass | pass |
| VERIFY-005 | Full harness | Eval tests | `pytest tests/evals/test_eval_harness.py` | pass | 33 passed | pass |
| VERIFY-006 | Regression suite | `python -m pytest -q` | pass | 615 passed | pass |
| VERIFY-007 | Types | `python -m mypy src` | pass | 96 files OK | pass |
| VERIFY-008 | Lint | `python -m ruff check src tests consumer_sdk evals` | pass | clean | pass |
| VERIFY-009 | CLI | `python -m evals.harness` | exit 0 | 24/24 PASS | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| `ledger_chain_integrity_failure` scenario | Startup refuse-to-start; not runnable in harness fixture model | Low — excluded per §13 n/a row |
| PolicyGate intake wiring | Out of TASK-026 scope | Low — policy_gate runner covers gate invariants |

## Follow-up hardening (2026-06-13)

- Added `evals/outcome_matrix.py` canonical SFE map keyed by `OutcomeMatrixFaultFlag`
- 10 new scenarios (24 total): correlation_failure, invalid_model_citation, provider_health_breaker_open, latency_sla_exceeded, queue_aging_exceeded, policy_ambiguity, rate_limit_exceeded, containment_breaker_open, ticket_stamp_failed, policy_gate_idempotency
- `_assert_outcome` fail-closed on missing SFE for escalate outcomes
- No `src/` production changes required
