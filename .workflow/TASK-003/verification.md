# Verification: TASK-003

Fresh evidence required before completion. Do not claim pass without actual results.

| ID | Check | Expected | Actual | Status |
|----|-------|----------|--------|--------|
| V-001 | Identical input → stable hash across calls | Same digest | pass | pass |
| V-002 | Object keys sorted by Unicode code point | Deterministic byte order | pass | pass |
| V-003 | Datetimes → UTC RFC3339, 6 fractional digits, `Z` | pass | pass | pass |
| V-004 | Invalid timestamp fractional digits rejected | `CanonicalSerializationError` | pass | pass |
| V-005 | `NaN`/`Infinity` raise | `CanonicalSerializationError` | pass | pass |
| V-006 | Unknown fields raise | `CanonicalSerializationError` | pass | pass |
| V-007 | Absent vs null serialize distinctly | Different bytes | pass | pass |
| V-008 | Length-delimited distinct from raw concat | pass | pass | pass |
| V-009 | Domain constants only in `domains.py` | grep clean | pass | pass |
| V-010 | `decision_id` five-part ordering (§3) | pass | pass | pass |
| V-011 | Idempotency key five-part ordering (§4) | pass | pass | pass |
| V-012 | `EMPTY_BUNDLE` preimage `praetor:v1:empty_bundle` (§7) | pinned in doc + code | pass | pass |
| V-013 | Feed `record_checksum` excludes checksum (§8.1) | pass | pass | pass |
| V-014 | Full `pytest -q` | all pass | 62 passed in 0.39s | pass |
| V-015 | No inline §2 domain literals outside `domains.py` | grep pass | pass | pass |
| V-016 | Never-contain entries hash (§9) | pass | pass | pass |
| V-017 | `stamp_id` four-part three-tuple (§5); distinct from decision/idempotency | pass | pass | pass |
| V-018 | `stamp_id` stable across processing attempts | same stamp, different decision_ids | pass | pass |
| V-019 | `docs/contracts.md` updated (doc-first contract fix) | §5 + §7 | pass | pass |
| V-020 | Other `docs/` files unchanged | scope guard | pass | pass |

**Status values:** `pending` | `pass` | `fail` | `skipped`

## Summary

- **Last run:** 2026-06-01 (post human review) — `pytest -q`
- **Overall:** pass

## Gaps / skipped checks

- Cross-Python patch-version determinism pin (single environment)
- CI / ruff / mypy
