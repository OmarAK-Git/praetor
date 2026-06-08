# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005 | Evidence citation unit tests | `python -m pytest -q tests/evidence/test_citation_validation.py` | Red before implementation, then pass | Red: `ModuleNotFoundError: No module named 'praetor.evidence'`; final: 7 passed | pass |
| VERIFY-002 | REQ-006 | Engine citation regression tests | `python -m pytest -q tests/engine/test_walking_skeleton.py tests/judgment/test_provider_failures.py` | pass | 15 passed | pass |
| VERIFY-003 | REQ-001-REQ-006 | Full test suite | `python -m pytest -q` | pass | Final: 366 passed; interim scope guard failure fixed by adding intentional `evidence` package to allowlist | pass |
| VERIFY-004 | REQ-001-REQ-006 | Type checking | `python -m mypy src` | pass | Success: no issues found in 74 source files; interim `model_dump(exclude=...)` type issue fixed | pass |
| VERIFY-005 | REQ-001-REQ-006 | Lint | `python -m ruff check src tests` | pass | All checks passed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| PolicyGate citation checks | PolicyGate is explicitly out of scope until TASK-017. | Shared validator must be integrated later when PolicyGate exists. |
| Real provider adversarial citation probing | Real provider probing is TASK-027. | Fake/structural tests cover deterministic validator behavior only. |
