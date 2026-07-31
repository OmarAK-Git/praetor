# Verifier result — agentic-judgment-01-provenance

## Verdict

**PASS**

## Claim restated

Task `agentic-judgment-01-provenance` is complete: `LEDGER_HISTORY` exists; `is_attacker_controllable_provenance(LEDGER_HISTORY)` is `False`; `WINDOWS_SECURITY_LOG` / `SYSMON_EVENT_LOG` classifications are unchanged; unknown paths remain attacker-controllable; scope limited to the provenance trust table (+ tests / workflow).

## Independent inspection

### `src/praetor/evidence/provenance.py`

Diff vs HEAD (only production change):

```diff
+LEDGER_HISTORY = "ledger_history"

-_NON_ATTACKER_CONTROLLABLE_PATHS = frozenset({WINDOWS_SECURITY_LOG})
+_NON_ATTACKER_CONTROLLABLE_PATHS = frozenset({WINDOWS_SECURITY_LOG, LEDGER_HISTORY})
```

- `LEDGER_HISTORY == "ledger_history"` (line 13)
- Membership in `_NON_ATTACKER_CONTROLLABLE_PATHS` makes `is_attacker_controllable_provenance` return `False` (lines 15, 26–27)
- `WINDOWS_SECURITY_LOG` still non-attacker; `SYSMON_EVENT_LOG` still in `_ATTACKER_CONTROLLABLE_OVERRIDES` → `True`
- Unknown paths still fall through to `return True` (line 30)
- `meets_account_corroboration` / `meets_host_cited_corroboration` bodies unchanged (PolicyGate logic untouched)

### `tests/evidence/test_provenance.py`

New untracked file; three tests map 1:1 to acceptance criteria (constant import + false for ledger; regression for security/sysmon; unknown `"some_new_source"` → True). Assertions call `is_attacker_controllable_provenance` directly (not stubs).

### Scope

`git status --short` for allowed paths:

- `M src/praetor/evidence/provenance.py`
- `?? tests/evidence/test_provenance.py`
- `?? .workflow/agentic-judgment-01-provenance/`

No unauthorized production-file edits observed for this task.

## Fresh command evidence

Worktree: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`  
`$env:PYTHONPATH = 'C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src'`

### `pytest tests/evidence/test_provenance.py -v`

```
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.3, pluggy-1.5.0
collected 3 items

tests/evidence/test_provenance.py::test_ledger_history_is_non_attacker_controllable PASSED [ 33%]
tests/evidence/test_provenance.py::test_existing_classifications_unchanged PASSED [ 66%]
tests/evidence/test_provenance.py::test_unknown_provenance_path_defaults_attacker_controllable PASSED [100%]

============================== 3 passed in 0.21s ==============================
```

Exit code: 0

### `ruff check src/praetor/evidence/provenance.py tests/evidence/test_provenance.py`

```
All checks passed!
```

Exit code: 0

### `mypy src/praetor/evidence/provenance.py`

```
Success: no issues found in 1 source file
```

Exit code: 0

## Acceptance criteria

| Criterion | Result |
|-----------|--------|
| `LEDGER_HISTORY` exists; `is_attacker_controllable_provenance(LEDGER_HISTORY)` is False | Met (code + fresh pytest) |
| `WINDOWS_SECURITY_LOG` / `SYSMON_EVENT_LOG` classifications unchanged | Met (code + fresh pytest) |
| Unknown provenance defaults attacker-controllable | Met (code + fresh pytest) |

## Adversarial checks (did not refute)

- Tests exercise the real function under worktree `PYTHONPATH`, not a mock.
- Diff is minimal (+constant, extend frozenset); corroboration helpers not rewritten.
- `LEDGER_HISTORY` not re-exported from `praetor.evidence.__init__` — out of Task 1 AC / plan allowed files; not a fail.
- DEC-064 decision-doc prose not added under this task’s allowed files — phase/sprint concern; ignored per packet `verification.scope` = task.

## Gaps

None for task-scoped verification.
