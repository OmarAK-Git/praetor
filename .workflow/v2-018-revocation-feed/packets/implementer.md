# Implementer Packet — V2-018 Revocation Supersession and Feed Verifiability

## Objective

Make supersession, expiry, feed projection, and consumer verification consistent per DEC-060.

## Original User Goal

V2-018 — Revocation supersession and feed verifiability: expired directive re-issue matches owner decision; feed supports consumer supersession verification or documents limitation.

## Relevant Docs and State

- `docs/proposals/v2_implementation_plan.md` § V2-018
- `docs/contracts.md` (feed/revocation contracts)
- DEC-060 owner decision on expired directive re-issue
- `.workflow/_dream/playbook.digest.md`

## Allowed Files

- `src/praetor/containment/lifecycle.py`
- `src/praetor/containment/revocation.py`
- `src/praetor/config/state.py`
- `src/praetor/revocation/exporter.py`
- `consumer_sdk/reference_verifier.py`
- `docs/contracts.md`
- `tests/containment/`
- `tests/consumer_sdk/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`
- `memory-bank/progress.md`
- `memory-bank/activeContext.md`

## Do-Not-Touch Boundaries

- Do not mark the queue item done
- Do not run phase/sprint exit verification
- Stop before dependency installs, harness config edits, clones, writes outside allowed files
- Do not implement V2-019 through V2-023

## Acceptance Criteria

1. Expired directive re-issue behavior matches the owner decision (DEC-060).
2. Expired-unrevoked outstanding rows do not create duplicate-suppression ambiguity.
3. Feed records expose enough information for consumers to verify supersession chains, or limitation is documented as consumer-local.
4. The verifier checks only V2-018 acceptance, not V2 Gate 3 completion.

## Verification Commands

```bash
pytest tests/containment/ tests/consumer_sdk/ -q
```

## Expected Result Schema

Write to `.workflow/v2-018-revocation-feed/results/implementer-result.md` with files changed, behavior summary, test additions, verification output, approval gates.
