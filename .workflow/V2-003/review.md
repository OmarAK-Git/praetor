# Review — V2-003

## Scope adherence

Decision-only task per V2-001/V2-002 pattern. No `src/` changes. Contracts and decisions updated; delivery backlog rows closed.

## Gaps logged

| Gap | Disposition | Owner task |
|---|---|---|
| Commit-time-only `snapshot_content` on every intake path | Explicitly **not** v1 contract per DEC-060 reopen; would be implementation work | Owning follow-on if product intent changes |
| Orphan health `SystemHealthAlert` not implemented | Documented in DEC-060; deferred | V2-010 |
| Activation/emergency revocation ledger-append unification | Out of V2-003 scope | V2-009 |
| Feed supersession consumer verifiability | Out of V2-003 scope | V2-018 |
| Optional expired-row archival purge | Not required for correctness | V2-010 |
| `docs/spec.md` not amended | Frozen; contracts §4.2.1/§7a carry V2 semantics | Spec unfreeze |

## Playbook alignment

- AG-0044: snapshot paired with edict at engine append — ratified in DEC-060.
- AG-0045: reconcile skips orphans — ratified; health surfacing added for V2-010.
- PE-0015: expired re-issue carve-out — ratified as DEC-060 § expired re-issue.

## REVIEW-007 / REVIEW-008 closure

Both open questions from TASK-017 `review.md` are closed by DEC-060. v1 `engine/edict.py` appends snapshot in the engine transaction; intake uses gate-supplied `live_never_contain_entries` for `snapshot_content` (orchestrator conflict path refreshes). `test_expired_directive_allows_fresh_reissue` asserts no revocation records.

## V2-003 reopen (2026-06-29)

Resolved ambiguous §7a wording ("commit time" vs gate evaluation). DEC-060 now pins gate-evaluation capture as the v1 intake contract; commit-time-only capture deferred to follow-on implementation if desired.
