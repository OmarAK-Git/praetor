# Implementer Packet — V2-022 SID and Normalizer Conformance

## Objective

Pin SID format validation vectors or documented v1 waiver; add normalizer conformance helpers for PE-0024 domain-separator ambiguity.

## Original User Goal

V2-022 — SID and normalizer conformance: SID validation vectors or documented waiver; malformed domain-separator accounts set ambiguity_flag=true in test helpers.

## Relevant Docs

- `docs/proposals/v2_implementation_plan.md` § V2-022
- PE-0024 (domain-separator ambiguity_flag rule)
- `docs/contracts.md` §11 (Windows SID form)

## Allowed Files

- `src/praetor/policy/identity.py`
- `src/praetor/correlation/`
- `tests/evidence/`
- `tests/correlation/`
- `specs/`, `IMPLEMENTATION_PLAN.md`, `memory-bank/*`

## Do-Not-Touch

- Do not mark queue item done
- Do not run full gate checks
- Stop before approval gates

## Acceptance Criteria

1. SID format validation has pass/fail vectors or a documented v1 waiver.
2. Future Windows normalizer test helpers require malformed domain-separator accounts to set ambiguity_flag=true.
3. Existing Sysmon and Security behavior stays pinned.
4. Verifier checks only V2-022, not V2 Gate 3.

## Verification

```bash
pytest tests/evidence/ tests/correlation/ -q
```

Write result to `.workflow/v2-022-sid-normalizer/results/implementer-result.md`
