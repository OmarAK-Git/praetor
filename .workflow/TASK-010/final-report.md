# Final Report: TASK-010 (revised)

## Status

**Complete** — hash-chained ledger with contracts pin, startup hook, hardened verification, and boundary tests.

## Deliverables

| Area | Files |
|------|-------|
| Ledger core | `src/praetor/ledger/{hash_chain,store,startup}.py` |
| Contracts pin | `docs/contracts.md` §7a |
| Hash domain | `src/praetor/hashing/domains.py` — `DOMAIN_LEDGER_LINK`, `compute_ledger_link_hash` |
| Model/schema | `DecisionEdict.ledger_previous_hash` nullable; `NeverContainSnapshotRecord` hash validator; `schemas/decision_edict.json` |
| Startup hook | `run_ledger_startup_hook` via `open_state_store` |
| Tests | `tests/ledger/` — **29** tests |

## Verification (2026-06-04)

```
pytest -q tests/ledger/  → 29 passed
pytest -q                → 285 passed
mypy src                 → OK (55 files)
ruff check (TASK-010 scope) → OK
python -m praetor.contracts.schema_export → OK
git diff docs/contracts.md → §7a only
```

## Known gaps (by design)

- Production append wiring for revocation/emergency/edict paths: Task 11–12
- Tail truncation undetectable without external anchor: documented in §7a

## safe_to_commit

**yes**
