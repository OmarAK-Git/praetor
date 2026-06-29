# Verification Ledger — V2-009

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Policy + emergency tests | `python -m pytest -q tests/policy/test_policy_gate.py tests/config/test_emergency_never_contain.py` | pass | pass | pass |
| VERIFY-002 | REQ-003 | Intake + harness | `python -m pytest -q tests/engine/test_intake_stamp_actuation.py tests/evals/test_eval_harness.py` | pass | pass | pass |
| VERIFY-003 | All scoped | V2-009 suite | `python -m pytest -q tests/policy tests/config/test_emergency_never_contain.py tests/config/test_config_activation.py tests/engine/test_intake_stamp_actuation.py tests/engine/test_crash_recovery.py tests/containment tests/evals/test_eval_harness.py` | pass | **154 passed** | pass |
| VERIFY-004 | Lint | mypy + ruff | `python -m mypy src evals consumer_sdk`; `python -m ruff check src tests evals consumer_sdk` | clean | clean | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Full `pytest -q` (797 tests) | 29 failures in worktree are pre-existing Windows/CRLF/splunk path issues unrelated to V2-009 diff | low — scoped suite green |
| Live Splunk | env-gated per AG-0007 | none |
