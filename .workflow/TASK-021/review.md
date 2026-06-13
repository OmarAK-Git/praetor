# Review

## Spec compliance review

- Implements `docs/contracts.md` §10 checks 1–5 in canonical order.
- Gatekeeper (2026-06-12): expiry skew fail-closed (DEC-037); superseded-directive hole closed; feed checksum verification added; truncation-tolerant gap (DEC-038); revocations honored in held records regardless of cursor.
- Lives outside `src/praetor/` per plan and spec.
- §10 item 6 (local consumer policy) intentionally omitted — not in plan test criteria.

## Code quality review

- SDK depends on `praetor.contracts` and `praetor.hashing` (including `compute_feed_record_checksum`).
- `src/praetor/py.typed` added; `consumer_sdk` under mypy packages.
- Structured `FailedCheck` enum includes `FEED_CHECKSUM_MISMATCH`.

## Risk review

- v1 feed projection cannot prove WHICH replacement a supersession record refers to (no `superseded_by` on feed line); `_supersession_feed_covers` documents this limit.
- Empty embedded never-contain subset supported (DEC-035).

## Human review notes

- Two probe-confirmed fail-open bugs (expiry skew direction, superseded-directive continue) fixed in gatekeeper pass.
