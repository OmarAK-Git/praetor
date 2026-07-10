# Verifier Result — V2-018 Revocation Supersession and Feed Verifiability

verification_model: claude-opus-4-8-thinking-high
outcome: pass

## Claim under test

Implementer claims V2-018 aligns expired re-issue, expired-unrevoked reconciliation, and
consumer feed supersession verification with DEC-060, with `pytest tests/containment/
tests/consumer_sdk/ -q` → 53 passed. Treated as unevidenced; re-derived below.

## Evidence gathered (self-run, not implementer transcript)

- `python -m pytest tests/containment/ tests/consumer_sdk/ -q` → **exit 0, 53 passed, 0 skipped** (re-run, 2.48s).
- `python -m pytest <7 named V2-018 tests> -v` → **7 collected, 7 passed** — confirms the new tests are actually collected and executed (not defined-but-uncollected):
  - `test_expired_unrevoked_rows_excluded_from_outstanding_fetch`
  - `test_reconcile_skips_expired_unrevoked_idempotency`
  - `test_revoke_supersession_rejects_expired_directive`
  - `test_validate_expired_reissue_carve_out_rejects_supersedes_link`
  - `test_supersession_feed_avoids_lineage_conflict`
  - `test_expired_prior_directive_allows_reissue_without_lineage_conflict`
  - `test_live_supersession_missing_feed_lineage_conflict`
- Read DEC-060 (`docs/decisions.md:161-230`) to fix the authoritative target; verified against source.

## Acceptance criteria (task-scoped)

**AC1 — Expired re-issue matches DEC-060.** SURVIVES.
- `directive_is_outstanding_by_expiry` (`lifecycle.py:27-34`) is real: `expires_at > now`.
- `validate_expired_reissue_carve_out` (`lifecycle.py:37-44`) raises `ValueError` when a
  replacement sets `supersedes_directive_id` — matches DEC-060 §4.2 ("supersedes unset").
- `revoke_supersession_in_transaction` (`revocation.py:68-92`) raises `SupersessionNotApplicableError`
  for a non-live (expired) directive before writing any record/feed row — matches "natural expiry
  is not supersession; no `DirectiveRevocationRecord`/feed row".
- Test setup is not gamed: expired directive `issued=NOW-1h, expires=+30s` genuinely yields
  `outstanding_by_expiry=False`; guard fires. Consumer side confirmed by
  `test_expired_prior_directive_allows_reissue_without_lineage_conflict` (expired prior → ACTIONABLE,
  no lineage conflict via real `_directive_is_live` skip at `reference_verifier.py:240-246`).

**AC2 — Expired-unrevoked rows create no duplicate-suppression ambiguity.** SURVIVES.
- `fetch_outstanding_unrevoked_directives` (`config/state.py:342-363`) filters `expires_at > ?`;
  `fetch_expired_unrevoked_directives` (`config/state.py:366-384`) filters `expires_at <= ?` —
  disjoint partitions on the same table.
- `reconcile_policy_state` step-6 (`policy/state.py:211-224`) iterates the **outstanding** fetch, so
  expired residue cannot re-register an idempotency key. `test_reconcile_skips_expired_unrevoked_idempotency`
  sets up a fully-paired edict+directive+idem_key and asserts `idempotency_keys_registered == 0` and
  `fetch_active_idempotency_key(...) is None` — proves the expired row is excluded (the key would
  register if the row were treated as outstanding). Robust: expiry (2026-06-11) is well before wall-clock.

**AC3 — Feed exposes supersession verifiability OR limitation documented consumer-local.** SURVIVES.
- `RevocationFeedRecord` (`contracts/feed.py:12-26`) genuinely **omits** `superseded_by_directive_id`;
  `build_feed_record` (`revocation/feed.py:30-57`) projects `reason_code` verbatim, and
  `RevocationReason.SUPERSESSION.value == "supersession"` (`contracts/ledger.py:24`) — so a real
  supersession revocation yields a feed row with `reason_code="supersession"`, exactly what the
  verifier matches.
- Limitation documented: `docs/contracts.md` §8.4 (`:366-377`) states the field is intentionally
  omitted and requires the two-signal consumer-local pairing (feed revocation proof + replacement
  `supersedes_directive_id`), failing closed via §10 item 5.
- Verifier implements it: `_supersession_feed_covers` + `_consumer_local_supersession_link` +
  `_has_lineage_conflict` (`reference_verifier.py:190-253`). Both positive
  (`test_supersession_feed_avoids_lineage_conflict` → ACTIONABLE) and negative
  (`test_live_supersession_missing_feed_lineage_conflict` → ESCALATE_HUMAN/LINEAGE_CONFLICT) paths
  exercise the real branches.

**AC4 — Task-scoped verification only.** Honored: checked V2-018 only; did not run V2 Gate 3 exit
or broader regression; phase-level gaps ignored per instructions.

## Refutation attempts that failed

- Gamed guards? No — error messages/match strings (`still-live`, `supersedes_directive_id`) map to
  real raised exceptions in source, not test-only constants.
- Tests that don't run new code? No — imported symbols resolve to the changed modules; running the
  7 tests by name collected and passed them.
- Weakened existing assertions? Read the full current `tests/consumer_sdk/test_reference_verifier.py`
  (569 lines): every existing test asserts both `outcome` and `failed_check`; nothing weakened. The
  file is modified as additive (6 new functions all present + passing).
- Stale evidence? All results are from fresh re-runs in this session.

## Residual limitation (non-blocking)

`git diff` for the modified test file could not complete — the Windows shell hung on the pager and
became unresponsive after repeated attempts. Mitigation: I read the entire *current* test file and
verified all assertions are strong; the modification is consistent with the claimed additive changes
and the by-name run confirms the new tests pass. This does not affect the verdict but the
removed-line diff was not independently obtained.

## Verdict

**survives / pass.** All four task-scoped acceptance criteria are supported by self-gathered,
non-stale evidence; tests exercise real code paths and are not gamed.
