# Implementer result — agentic-judgment-01-provenance

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/evidence/provenance.py` | Added `LEDGER_HISTORY` constant and included it in `_NON_ATTACKER_CONTROLLABLE_PATHS` (DEC-064). |
| `tests/evidence/test_provenance.py` | New unit tests for ledger_history classification and regression guards for existing paths. |

## TDD evidence

1. **Failing test (Step 2):** `pytest tests/evidence/test_provenance.py -v` → `ImportError: cannot import name 'LEDGER_HISTORY'` (expected).
2. **Passing test (Step 4):** All 3 tests pass after implementation.

## Verification commands and outcomes

### `pytest tests/evidence/test_provenance.py -v`

```
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.3, pluggy-1.5.0
collected 3 items

tests/evidence/test_provenance.py::test_ledger_history_is_non_attacker_controllable PASSED [ 33%]
tests/evidence/test_provenance.py::test_existing_classifications_unchanged PASSED [ 66%]
tests/evidence/test_provenance.py::test_unknown_provenance_path_defaults_attacker_controllable PASSED [100%]

============================== 3 passed in 0.18s ==============================
```

### `ruff check src/praetor/evidence/provenance.py tests/evidence/test_provenance.py`

```
All checks passed!
```

### `mypy src/praetor/evidence/provenance.py`

```
Success: no issues found in 1 source file
```

## Acceptance criteria status

- [x] `LEDGER_HISTORY` constant exists and `is_attacker_controllable_provenance(LEDGER_HISTORY)` is `False`.
- [x] Existing `WINDOWS_SECURITY_LOG` / `SYSMON_EVENT_LOG` classifications unchanged.
- [x] Unknown provenance paths still default to attacker-controllable.

## Gaps

None. Task 1 complete per plan; commit intentionally skipped per packet constraints.
