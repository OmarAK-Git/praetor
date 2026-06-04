# Verification Ledger: TASK-010 (revised)

Recorded from repository root.

| ID | Requirement | Command | Expected | Actual | Status |
|----|-------------|---------|----------|--------|--------|
| VERIFY-001 | Ledger tests | `pytest -q tests/ledger/` | pass | **35 passed** | pass |
| VERIFY-002 | Full suite | `pytest -q` | pass | **291 passed** | pass |
| VERIFY-003 | Types | `mypy src` | pass | Success: 55 source files | pass |
| VERIFY-004 | TASK-010 scoped lint | see below | pass | All checks passed | pass |
| VERIFY-005 | contracts §7a pin | `git diff docs/contracts.md` | §7a only | §7a ledger link added | pass |
| VERIFY-006 | Schema nullable + drift | `tests/contracts/test_schema_export.py` | pass | 2 new drift/nullable tests | pass |
| VERIFY-007 | Schema export | `python -m praetor.contracts.schema_export` | pass | 14 files written | pass |
| VERIFY-008 | Startup hook | `test_open_state_store_refuses_tampered_ledger` | alert + refuse | pass | pass |
| VERIFY-009 | Error normalization | `tests/ledger/test_error_normalization.py` | LedgerChainIntegrityError | pass | pass |
| VERIFY-010 | Audit relationship | `tests/ledger/test_audit_relationship.py` | match/mismatch | pass | pass |
| VERIFY-011 | Deletion boundary | `tests/ledger/test_chain_deletion.py` | middle fail / tail pass | pass | pass |
| VERIFY-012 | Link test vector | `tests/ledger/test_ledger_link_vector.py` | §7a hash | pass | pass |

## VERIFY-004 command

```text
ruff check src/praetor/ledger tests/ledger src/praetor/hashing/domains.py src/praetor/contracts/edict.py src/praetor/state/store.py tests/contracts/test_schema_export.py tests/contracts/conftest.py
```

## Skipped checks

| Check | Reason | Risk |
|-------|--------|------|
| Repo-wide ruff | Pre-existing E501/UP042 in unrelated files | Low |
| Task 11–12 integration | Out of scope | Expected |

## safe_to_commit

**yes**
