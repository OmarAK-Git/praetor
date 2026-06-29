# Review — V2-010

## REVIEW-001 — Recovery downgrade retained

**Decision:** Retain existing `_recovery_disposition_for_stamp` downgrade (PE-0007); do not replace with PolicyGate re-evaluation.

**Rationale:** v1 recovery path is intentionally conservative; re-running PolicyGate at recovery would reintroduce containment eligibility and violate DEC-060 recovery safety posture.

## REVIEW-002 — Orphan surfacing

**Decision:** Emit `orphan_outstanding_directive` health alert per orphan directive_id; stable alert_id `orphan-directive-{directive_id}` for idempotency.

**Rationale:** DEC-060 requires operator visibility; purge forbidden without recovery context.

## REVIEW-003 — Expired-row archival

**Decision:** Deferred (optional per DEC-060).

## REVIEW-004 — Docs gap

**Decision:** `docs/operator_runbook.md` not updated (task hard limit). Alert code `orphan_outstanding_directive` is implemented but runbook prose deferred.

## Environmental note

Full `pytest -q` on this worktree (V2-005 base) reports ~30 failures unrelated to V2-010 (Windows CRLF schema export, correlation fixture manifest checksums). Main workspace at V2-006 WIP reports 797 passed / 2 failed. V2-010 scoped suites: **247 passed** (engine/policy/containment/runtime/ledger/state/alerts).
