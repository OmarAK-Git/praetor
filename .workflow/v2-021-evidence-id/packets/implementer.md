# Implementer Packet — V2-021 Evidence ID Contract Pin

## Objective

Pin evidence_id contract in docs and tests; close DEC-051.

## Original User Goal

V2-021 — Evidence ID contract pin: docs/contracts.md defines evidence_id preimage; exact test vector pins one known evidence_id.

## Relevant Docs

- `docs/contracts.md` (read before hashing code)
- `docs/proposals/v2_implementation_plan.md` § V2-021
- DEC-051

## Allowed Files

- `docs/contracts.md`
- `src/praetor/hashing/domains.py`
- `src/praetor/correlation/ids.py`
- `tests/hashing/`
- `tests/correlation/`
- `specs/`, `IMPLEMENTATION_PLAN.md`, `memory-bank/*`

## Do-Not-Touch

- Do not mark queue item done
- Do not run full gate checks
- Stop before approval gates

## Acceptance Criteria

1. docs/contracts.md defines evidence_id preimage, domain constant, and input ordering.
2. Exact test vector pins one known evidence_id.
3. Domain literal isolation check still passes.
4. DEC-051 is no longer an open doc decision.
5. Verifier checks only V2-021, not V2 Gate 3.

## Verification

```bash
pytest tests/hashing/ tests/correlation/ -q
```

Write result to `.workflow/v2-021-evidence-id/results/implementer-result.md`
