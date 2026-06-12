# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–006 | Containment lifecycle tests | `python -m pytest -q tests/containment/test_directive_lifecycle.py` | pass | 15 passed | pass |
| VERIFY-002 | REQ-007–011 | Containment revocation tests | `python -m pytest -q tests/containment/test_revocation.py` | pass | 8 passed | pass |
| VERIFY-003 | AC-003 | Full regression | `python -m pytest -q` | pass | 485 passed in 37.72s | pass |
| VERIFY-004 | AC-003 | Type check | `python -m mypy src` | clean | 88 files OK | pass |
| VERIFY-005 | AC-003 | Lint | `python -m ruff check src tests` | clean | All checks passed | pass |
| VERIFY-006 | Gatekeeper item 1 | Manual revocation ledger + chain | `test_manual_revocation_clears_key_in_one_tx` | pass | pass | pass |
| VERIFY-007 | Gatekeeper item 2 | Mid-export feed floor | `test_minimum_feed_sequence_excludes_pending_unexported` | pass | pass | pass |
| VERIFY-008 | Gatekeeper item 6 | Emergency atomicity | `test_emergency_conflict_revocation_rolls_back_on_injected_failure` | pass | pass | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
