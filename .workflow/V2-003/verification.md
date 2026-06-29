# Verification Ledger — V2-003

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | DEC-060 + §7a | `rg "DEC-060" docs/decisions.md` + §7a read | Snapshot append site documented | §7a "NeverContainSnapshotRecord append site" + DEC-060 § | pass |
| VERIFY-002 | REQ-002 | §4.2 expired carve-out | §4.2 read + `test_expired_directive_allows_fresh_reissue` | No revocation on expiry | §4.2 second bullet; test asserts `revocations == []` | pass |
| VERIFY-003 | REQ-003 | §4.2.1 startup | §4.2.1 read | Expired rows excluded from step 6 | `expires_at > now` filter documented | pass |
| VERIFY-004 | REQ-004 | §4.2.1 orphans | §4.2.1 + `test_reconcile_skips_idempotency_when_ledger_edict_missing` | Skip + V2-010 health | Documented; existing test passes | pass |
| VERIFY-005 | Backlog | delivery_backlog | `rg "DEC-060" docs/proposals/delivery_backlog.md` | REVIEW-007/008 closed | 4 rows resolved | pass |
| VERIFY-006 | No regression | Default pytest gate | `python -m pytest -q` | pass | **780 passed**, 2 deselected, 1 xfailed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Full `mypy src` | No `src/` changes | None |
| New behavioral tests | Decision-only; V2-010/V2-018 own implementation tests | Low — contracts + DEC-060 are SSOT |

## Verification run (2026-06-29)

```
python -m pytest -q
rg "DEC-060" docs/
```

Results recorded in final-report.
