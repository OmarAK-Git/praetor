# Verification Ledger — V2-001

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–003, REQ-005 | DEC-058 decision content | `rg "DEC-058" docs/decisions.md` + section read | Posture, actions, escalate blocks, precedence documented | Present in `docs/decisions.md` DEC-058 section | pass |
| VERIFY-002 | REQ-004 | v2_hardening ratification | `rg "DEC-058" docs/proposals/v2_hardening.md` | Item 2 checklist marked ratified | `[x] Item 2` + DEC-058 reference | pass |
| VERIFY-003 | Backlog unblocked | delivery_backlog status | `rg "DEC-058" docs/proposals/delivery_backlog.md` | Authorization model row resolved | 3 rows reference DEC-058 | pass |
| VERIFY-004 | No regression | Default pytest gate | `python -m pytest -q` | pass | **780 passed**, 2 deselected, 1 xfailed | pass |
| VERIFY-005 | Scope guard lint | Ruff on touched test | `python -m ruff check tests/contracts/test_scope_guard.py` | clean | All checks passed | pass |
| VERIFY-006 | Scope guard types | Mypy on touched test | `python -m mypy tests/contracts/test_scope_guard.py` | clean | Success: no issues found in 1 source file | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| New doc test for DEC-058 | Decision-only task; grep + manual read sufficient | Low — decision text is static markdown |
| Full `mypy src` / repo-wide ruff | No `src/` changes; scoped static checks on touched test file only | None |

## Verification run (2026-06-29)

```
python -m pytest -q
python -m ruff check tests/contracts/test_scope_guard.py
python -m mypy tests/contracts/test_scope_guard.py
```

Results recorded in final-report.
