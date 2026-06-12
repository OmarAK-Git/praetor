# Final Report: TASK-020

## Summary

Complete including gatekeeper follow-up. `praetor.containment` consolidates directive lifecycle and differentiated revocation. Manual revocation now appends to the hash-chained ledger in the same transaction as feed projection and key clear (DEC-034).

## Gatekeeper follow-up (2026-06-11)

| Item | Change |
|---|---|
| Manual revocation ledger | `manual_revoke_directive_in_transaction` mirrors automated path; `verify_ledger_chain` test |
| Feed floor mid-export | Tests for exported seq 1 + pending seq 2 → floor 1; fresh DB → floor 0 |
| §9 hash coverage | Negative tamper tests; non-empty embedded round-trip |
| Builder hardening | `require_critical_transaction`; caller `live_never_contain_entries` as sole embed source |
| Trigger assertions | `reason` + alert count per revoked directive |
| Emergency atomicity | Fault-injection hook; no emergency/revocation/feed/ledger on rollback |

## Files changed

- `src/praetor/containment/{lifecycle,revocation}.py`
- `src/praetor/state/store.py` (`write_manual_revocation_in_transaction`)
- `src/praetor/config/emergency.py` (test hook)
- `tests/containment/*`, `tests/policy/test_directive_embedded_hash.py`
- `memory-bank/{decisions,activeContext,progress}.md`
- `.workflow/TASK-020/*`

## Verification performed

```
python -m pytest -q tests/containment/test_directive_lifecycle.py
15 passed

python -m pytest -q tests/containment/test_revocation.py
8 passed

python -m pytest -q tests/containment/
23 passed

python -m pytest -q
485 passed in 37.72s

python -m mypy src
Success: no issues found in 88 source files

python -m ruff check src tests
All checks passed!
```

## Known gaps

- Supersession not exercised by PolicyGate v1.
- Empty embedded subset typical at emission (DEC-035).
- Engine orchestrator PolicyGate wiring deferred.

## safe_to_commit

yes — 485 passed, mypy clean, ruff clean
