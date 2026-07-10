# Workflow Plan — V2-019 Ledger Tip Anchor and Feed Floor Hardening

## Goal

V2-019 — Ledger tip anchor and feed floor hardening: runbook documents tail-truncation; feed exporter reconciles metadata floor against on-disk JSONL.

## Scope

Ledger/feed integrity limits and operator visibility only. Do not run V2 Gate 3 exit.

## Tier

T2

## Acceptance Criteria

1. Runbook documents tail-truncation limitation and an out-of-band tip-anchor procedure.
2. Optional verifier hook compares current ledger tip against an operator-supplied anchor.
3. Feed exporter reconciles metadata floor against the on-disk JSONL artifact and marks stale metadata unhealthy.
4. Verifier checks only V2-019 acceptance, not V2 Gate 3 completion.

## Implementation Steps

1. Add `verify_ledger_tip_against_anchor` optional hook in `src/praetor/ledger/tip_anchor.py`.
2. Document tip anchor and feed metadata reconciliation in `docs/contracts.md` and `docs/operator_runbook.md`.
3. Expose `reconcile_feed_metadata_against_jsonl` in exporter; call at startup before export drain.
4. Add ledger tip-anchor tests and feed reconciliation tests.

## Verification Commands

```bash
pytest tests/ledger/ tests/revocation/ -q
```
