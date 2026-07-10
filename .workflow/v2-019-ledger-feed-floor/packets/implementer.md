# Implementer Packet — V2-019 Ledger Tip Anchor and Feed Floor Hardening

## Objective

Document ledger tail-truncation limits, add optional tip-anchor verifier hook, and harden feed metadata floor reconciliation against on-disk JSONL.

## Original User Goal

V2-019 — Ledger tip anchor and feed floor hardening: runbook documents tail-truncation; feed exporter reconciles metadata floor against on-disk JSONL.

## Relevant Docs and State

- `docs/proposals/v2_implementation_plan.md` § V2-019
- `docs/contracts.md` §7a (chain boundaries), §8.3 (feed floor)
- AG-0027 (tail truncation / tip anchor), AG-0030 (metadata vs artifact), AG-0055 (verified-exported floor)
- `.workflow/_dream/playbook.digest.md`

## Allowed Files

- `src/praetor/ledger/`
- `src/praetor/revocation/exporter.py`
- `docs/contracts.md`
- `docs/operator_runbook.md`
- `tests/ledger/`
- `tests/revocation/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`
- `memory-bank/progress.md`
- `memory-bank/activeContext.md`

## Do-Not-Touch Boundaries

- Do not mark the queue item done
- Do not run phase/sprint exit verification
- Stop before dependency installs, harness config edits, clones, writes outside allowed files
- Do not implement V2-020 through V2-023

## Acceptance Criteria

1. Runbook documents tail-truncation limitation and an out-of-band tip-anchor procedure.
2. Optional verifier hook compares current ledger tip against an operator-supplied anchor.
3. Feed exporter reconciles metadata floor against the on-disk JSONL artifact and marks stale metadata unhealthy.
4. The verifier checks only V2-019 acceptance, not V2 Gate 3 completion.

## Verification Commands

```bash
pytest tests/ledger/ tests/revocation/ -q
```

## Expected Result Schema

Write to `.workflow/v2-019-ledger-feed-floor/results/implementer-result.md` with files changed, behavior summary, test additions, verification output, approval gates.
