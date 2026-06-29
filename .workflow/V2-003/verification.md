# Verification Ledger — V2-003

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | DEC-060 + §7a | `rg "DEC-060" docs/decisions.md` + §7a read | Append site + gate-evaluation `snapshot_content` timing | §7a timing subsection + DEC-060 § timing | pass |
| VERIFY-002 | REQ-002 | §4.2 expired carve-out | §4.2 read + `test_expired_directive_allows_fresh_reissue` | No revocation on expiry | Unchanged | pass |
| VERIFY-003 | REQ-003 | §4.2.1 startup | §4.2.1 read | Expired rows excluded from step 6 | Unchanged | pass |
| VERIFY-004 | REQ-004 | §4.2.1 orphans | §4.2.1 + existing test | Skip + V2-010 health | Unchanged | pass |
| VERIFY-005 | Backlog | delivery_backlog | `rg "DEC-060" docs/proposals/delivery_backlog.md` | REVIEW-007/008 closed | Unchanged | pass |
| VERIFY-006 | No regression | Default pytest gate | `python -m pytest -q` | pass | **785 passed**, 2 deselected, 1 xfailed | pass |
| VERIFY-007 | Reopen | `snapshot_content` timing grep | `rg "gate-evaluation capture|gate-supplied" docs/` | Explicit v1 meaning | hits in decisions + contracts §7a | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Full `mypy src` | No `src/` changes | None |
| New behavioral tests | Docs-only reopen per user request | None |

## Verification run (2026-06-29 reopen)

```
python -m pytest -q
rg "DEC-060" docs/
rg "gate-evaluation capture|gate-supplied" docs/
```

Results recorded in final-report.
