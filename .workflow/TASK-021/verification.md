# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–010 | Consumer SDK tests | `python -m pytest -q tests/consumer_sdk/test_reference_verifier.py` | pass | 24 passed | pass |
| VERIFY-002 | AC-002 | Full regression | `python -m pytest -q` | pass | 509 passed in 35.21s | pass |
| VERIFY-003 | AC-002 | Type check | `python -m mypy src consumer_sdk` | clean | 90 files OK | pass |
| VERIFY-004 | AC-002 | Lint | `python -m ruff check src tests consumer_sdk` | clean | All checks passed | pass |
| VERIFY-005 | GK-001 | Expiry skew fail-closed | `test_expired_one_second_past_expires_at_non_actionable`, `test_expired_within_skew_window_before_nominal_expiry` | pass | pass | pass |
| VERIFY-006 | GK-002 | Superseded-directive hole | `test_superseded_old_directive_with_live_replacement_escalates` | pass | pass | pass |
| VERIFY-007 | GK-003 | Feed checksum | `test_feed_checksum_mismatch_escalates` | pass | pass | pass |
| VERIFY-008 | GK-005 | Truncation-tolerant gap | `test_truncated_window_starting_above_one_passes`, `test_cursor_beyond_retained_window_max_is_gap` | pass | pass | pass |
| VERIFY-009 | GK-006 | Revocation in hand | `test_revocation_beyond_cursor_in_hand_non_actionable` | pass | pass | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| `docs/contracts.md` update | start-task hard limit | plan file list includes doc; §10 already authoritative |
