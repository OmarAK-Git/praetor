# Implementer result — corroboration-floor-02-helpers

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/evidence/provenance.py` | DEC-065 temporary floor: host ≥1 anchoring cite (sole ambiguity fails); account ≥1 fact; `LEDGER_HISTORY` removed from non-attacker set |
| `tests/evidence/test_host_corroboration.py` | Inverted single-provenance / dual-attacker-path expectations to pass; zero-anchor cases now pass when one cite anchors |
| `tests/evidence/test_account_corroboration.py` | Inverted ≥2-path expectations; updated eligibility tests for ≥1 floor; added orchestrator pre-import for isolated collection |
| `tests/evidence/test_provenance.py` | `LEDGER_HISTORY` now attacker-controllable (`True`) |

## Implementation summary

### `meets_host_cited_corroboration`
- Fail when zero target-anchoring cites.
- Fail when exactly one anchoring cite has `ambiguity_flag=true`.
- Pass when ≥1 anchoring cite and not sole-ambiguous.
- Removed distinct-path ≥2 and trusted-path (`is_attacker_controllable_provenance`) checks.

### `meets_account_corroboration`
- Pass when `len(facts) >= 1` (any provenance).
- Fail when empty.

### `LEDGER_HISTORY`
- Constant retained.
- Removed from `_NON_ATTACKER_CONTROLLABLE_PATHS`; `is_attacker_controllable_provenance(LEDGER_HISTORY)` is `True`.

## Verification

```
pytest tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py -q
33 passed in 0.33s

ruff check src/praetor/evidence/provenance.py tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py
All checks passed!

mypy src/praetor/evidence/provenance.py
Success: no issues found in 1 source file
```

## Notes

- `test_account_corroboration.py` requires `import praetor.engine.orchestrator` before `praetor.policy.identity` to avoid a pre-existing policy↔engine circular import when the evidence suite runs in isolation.
- Policy gate / harness updates are out of scope (Task 3).

## Unresolved

- None within task scope.
