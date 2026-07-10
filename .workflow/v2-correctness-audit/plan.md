# Plan — v2-correctness-audit

## Goal

Correctness check of completed V2 build: spec drift, walkthrough/tests for fallen invariants, homogeneity (no over-engineering), design-decision recording completeness; then refresh README and related stale docs. Spec and implementation plan edits require user permission.

## Tier

T2 (audit + doc refresh; no product code changes unless audit finds blocking defects)

## Scope

- Read-only correctness audit of V2 vs plan/contracts/decisions/code/tests
- Fresh verification: pytest, ruff, mypy, walkthrough checker, eval harness as needed
- Update README and stale operational/demo docs
- Ask before editing `docs/spec.md` or `docs/proposals/v2_implementation_plan.md`

## Acceptance criteria

1. Spec/plan drift findings documented with evidence (or clean bill).
2. Fresh test/walkthrough/lint/typecheck evidence recorded.
3. Homogeneity / over-build assessment recorded.
4. Design-decision recording gaps listed (or confirmed complete).
5. README + related stale docs updated; Spec/plan only if user approves.

## Verification

```
pytest -q
ruff check .
mypy .
python notebooks/check_walkthrough.py
```
