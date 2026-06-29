# Verification Ledger — V2-005

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | String scope preflight | `pytest tests/config/test_org_config_loader.py -q -k global` | pass | 1 passed | pass |
| VERIFY-001b | REQ-001 | Malformed object scope | `pytest tests/config/test_org_config_loader.py -q -k malformed_object_scope` | pass | 2 passed | pass |
| VERIFY-002 | REQ-002 | Unknown keys | `pytest tests/config/ -q -k unknown_containment` | pass | 2 passed | pass |
| VERIFY-003 | REQ-003 | Scope round-trip | `pytest tests/config/test_org_config_loader.py -q -k round_trip` | pass | 1 passed | pass |
| VERIFY-004 | REQ-004 | Example config hash | `pytest tests/config/test_org_config_loader.py -q -k stable_snapshot` | pass | 1 passed | pass |
| VERIFY-005 | REQ-005 | Catch-all gate match | `pytest tests/policy/test_containment_policy.py -q -k catch_all` | pass | 1 passed | pass |
| VERIFY-006 | VS-0001 | Full gate | `python -m pytest -q` | pass | **793 passed**, 2 deselected, 1 xfailed | pass |
| VERIFY-007 | VS-0001 | Mypy | `python -m mypy src evals consumer_sdk` | clean | **118** files, no issues | pass |
| VERIFY-008 | VS-0001 | Ruff | `python -m ruff check src tests evals consumer_sdk` | clean | All checks passed | pass |

## Reopen (2026-06-29)

- Fixed ruff **E501** in `containment_policy.py` (line wrap only; semantics unchanged).
- Added `test_malformed_object_scope_fails_preflight` (`catch_all: false`, mixed scope keys) → `invalid_containment_rule_scope`.

## Verification run (2026-06-29 reopen)

```
python -m pytest -q
python -m mypy src evals consumer_sdk
python -m ruff check src tests evals consumer_sdk
pytest tests/config/test_org_config_loader.py -q -k "global or malformed_object_scope or round_trip or stable_snapshot"
pytest tests/config/ -q -k unknown_containment
pytest tests/policy/test_containment_policy.py -q -k catch_all
```
