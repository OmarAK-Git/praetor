# Implementer Result — V2-021 Evidence ID Contract Pin

**implementation_model:** composer-2.5-fast

## Summary

Pinned `evidence_id` derivation in `docs/contracts.md` §3b (preimage, domain constant, input ordering, test vector). Added contract tests and extended domain-literal isolation. Closed DEC-051 doc decision in `memory-bank/decisions.md`.

## Files Changed

| File | Rationale |
|---|---|
| `docs/contracts.md` | Added `DOMAIN_EVIDENCE_ID` to §2 table; new §3b documents preimage, ordering, `source_event_reference` form, and pinned test vector |
| `src/praetor/correlation/ids.py` | Docstring references contracts §3b |
| `tests/correlation/test_evidence_id.py` | Contract vector, delimited-ordering, and `source_event_reference` canonical-form tests |
| `tests/hashing/test_canonical.py` | Extended domain-constant and inline-literal isolation checks to include `praetor:v1:evidence_id` |
| `memory-bank/decisions.md` | DEC-051 updated — doc decision closed; contracts §3b is authoritative |

## Verification

```bash
pytest tests/hashing/ tests/correlation/ -q
```

**Result:** `57 passed in 0.72s` (exit code 0)

## Acceptance Criteria

| Criterion | Status |
|---|---|
| `docs/contracts.md` defines evidence_id preimage, domain constant, and input ordering | ✅ §3b |
| Exact test vector pins one known evidence_id | ✅ `ev-d874f190dca015a7ba7235e2e933fbd2` |
| Domain literal isolation check still passes | ✅ includes `praetor:v1:evidence_id` |
| DEC-051 is no longer an open doc decision | ✅ memory-bank updated |
| Queue item not marked done | ✅ not touched |

## Unresolved

- `docs/decisions.md` DEC-051 row not updated (outside allowed write scope); `memory-bank/decisions.md` carries the closure.

---

## Retry — AC4 doc closure (packet defect fix)

**Trigger:** Verifier refuted AC4 only — authoritative docs still marked DEC-051 Open.

**Files changed (retry write scope):**

| File | Rationale |
|---|---|
| `docs/decisions.md` | DEC-051 row updated — doc decision closed; contracts §3b is authoritative for derivation |
| `docs/proposals/delivery_backlog.md` | DEC-051 backlog item status → **Done (DEC-051, V2-021)** |

**Verification (retry):**

```bash
pytest tests/hashing/ tests/correlation/ -q
```

**Result:** `57 passed in 0.71s` (exit code 0)

**AC4 status (retry):** ✅ `docs/decisions.md` no longer contains "open doc decision" for DEC-051; `delivery_backlog.md` status is Done.

**Queue:** Not marked done (per controller instruction).
