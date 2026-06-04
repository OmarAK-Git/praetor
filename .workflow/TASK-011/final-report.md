# Final Report: TASK-011 (reopened hardening)

## Status

**Complete** — revocation feed exporter, startup recovery, feed-prefix/metadata integrity, smoke benchmark.

## Deliverables

| Area | Files |
|------|-------|
| Revocation package | `src/praetor/revocation/{outbox,feed,exporter}.py` |
| Store hook | `open_state_store` — export schema + feed startup when org config active |
| Benchmark | `benchmarks/smoke_serialized_path.py` |
| Tests | `tests/revocation/` (**19**), `tests/runtime/test_feed_startup_recovery.py` (**4**), `tests/benchmarks/` (**2**) |
| Scope guard | `revocation` package allowed |

## Verification (2026-06-04, reopened)

```
pytest -q tests/revocation/                              → 19 passed
pytest -q tests/runtime/test_feed_startup_recovery.py  → 4 passed
pytest -q tests/benchmarks/                              → 2 passed
pytest -q tests/revocation/ tests/runtime/test_feed_startup_recovery.py tests/benchmarks/
                                                         → 25 passed (focused)
pytest -q                                                → 316 passed (full suite)
mypy src/praetor/revocation                            → OK
```

## Hardening (reopen)

- Checksum hard failure, crash replay, unhealthy recovery, sequence gaps, canonical timestamps
- Active-config smoke benchmark targets
- Feed prefix vs authoritative projection
- Corrupt / duplicate / out-of-order prefix lines
- **Metadata vs on-disk:** `last_verified_exported_sequence` must not exceed validated on-disk prefix; missing/empty file when metadata claims export → unhealthy
- **Schema-invalid JSON:** Pydantic / shape errors → `FeedChecksumError` → unhealthy (no crash)

## Known gaps (by design)

- PolicyGate integration: Task 16
- Walking skeleton / ledger append on revocation: Task 12
- Operator feed path configuration: Task 35

## safe_to_commit

**yes**
