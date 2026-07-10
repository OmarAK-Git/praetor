# Implementer Packet — V2-023 Contract Scope Guard and Generated Artifact Hygiene

## Objective

Harden contract drift controls: strict scope-guard allowlists for sanctioned V2 packages/docs, and schema generator CLI with `--check` / `--write`.

## Original User Goal

V2-023 — Contract scope guard and generated artifact hygiene: scope guard allowlist strict; generators expose `--check` and `--write`.

## Relevant Docs

- `docs/proposals/v2_implementation_plan.md` § V2-023
- GR-0009 (generator `--check` / `--write` hygiene)
- AG-0001, AG-0095 (scope-guard allowlist rules)

## Allowed Files

- `tests/contracts/test_scope_guard.py`
- `schemas/`
- `tools/`
- `docs/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`, `memory-bank/progress.md`, `memory-bank/activeContext.md`

## Do-Not-Touch

- Do not mark queue item done
- Do not run V2 Gate 3 exit
- Do not modify `src/` production code

## Acceptance Criteria

1. Scope guard allowlist covers sanctioned V2 docs and source packages only.
2. Generated schema artifacts remain deterministic after schema changes.
3. Schema generator exposes `--check` and `--write` where applicable.
4. Verifier checks only V2-023, not V2 Gate 3 completion.

## Verification

```bash
pytest tests/contracts/test_scope_guard.py -q
```

Write result to `.workflow/v2-023-scope-guard/results/implementer-result.md`
