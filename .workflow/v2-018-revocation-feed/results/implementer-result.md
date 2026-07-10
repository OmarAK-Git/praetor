# Implementer Result — V2-018 Revocation Supersession and Feed Verifiability

implementation_model: composer-2.5-fast

## Summary

Aligned revocation supersession, expired re-issue, and consumer feed verification with DEC-060:

- **Expired re-issue (DEC-060 §4.2):** Added `directive_is_outstanding_by_expiry`, `validate_expired_reissue_carve_out`, and `SupersessionNotApplicableError` guard on `revoke_supersession_in_transaction` so natural expiry cannot produce a supersession revocation/feed row.
- **Duplicate-suppression clarity:** Added `fetch_expired_unrevoked_directives` and tests proving expired audit-residue rows are excluded from outstanding scans and startup step-6 idempotency re-registration.
- **Feed supersession verifiability:** Documented consumer-local limitation in `docs/contracts.md` §8.4; clarified exporter and reference verifier pairing of feed `reason_code=supersession` with replacement-directive `supersedes_directive_id`.

## Files Changed

| File | Rationale |
|---|---|
| `src/praetor/containment/lifecycle.py` | DEC-060 expiry/outstanding helpers and expired re-issue carve-out validator |
| `src/praetor/containment/revocation.py` | Reject supersession revocation for expired directives |
| `src/praetor/config/state.py` | `fetch_expired_unrevoked_directives` for audit-residue visibility |
| `src/praetor/revocation/exporter.py` | Module doc pin for §8.4 feed projection limitation |
| `consumer_sdk/reference_verifier.py` | Supersession feed + consumer-local linkage checks and docs |
| `docs/contracts.md` | New §8.4 supersession feed projection / consumer-local linkage |
| `tests/containment/test_dec060_revocation_feed.py` | DEC-060 expiry, reconcile, and supersession guard tests |
| `tests/consumer_sdk/test_reference_verifier.py` | Expired re-issue and live supersession feed coverage tests |

## Test Additions

- `test_expired_unrevoked_rows_excluded_from_outstanding_fetch`
- `test_reconcile_skips_expired_unrevoked_idempotency`
- `test_revoke_supersession_rejects_expired_directive`
- `test_validate_expired_reissue_carve_out_rejects_supersedes_link`
- `test_expired_prior_directive_allows_reissue_without_lineage_conflict`
- `test_live_supersession_missing_feed_lineage_conflict`

## Verification Output

```text
$ pytest tests/containment/ tests/consumer_sdk/ -q
.....................................................                    [100%]
53 passed in 2.57s
```

## Approval Gates

- Queue item **not** marked done (per implementer packet).
- Full gate / sprint exit checks **not** run (per implementer packet).
- Scope limited to `files_allowed`; V2-019+ untouched.

## Unresolved

None.
