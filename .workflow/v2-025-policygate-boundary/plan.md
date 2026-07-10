# Workflow Plan — V2-025 All Containment Through PolicyGate

## Goal

V2-025 — All containment through PolicyGate: no production caller authorizes account or host containment via lower eligibility helpers; static guard catches direct calls; integration tests prove the feature gate cannot be bypassed.

## Scope

PolicyGate authorization boundary enforcement only. Do not run V2 Gate 4 exit.

## Tier

T2

## Allowed Files

- `src/praetor/policy/identity.py`
- `src/praetor/policy/gate.py`
- `tests/contracts/`
- `tests/policy/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`, `memory-bank/progress.md`, `memory-bank/activeContext.md`

## Acceptance Criteria

1. No production caller authorizes account or host containment by calling lower eligibility helpers directly.
2. Static grep/AST guard catches direct calls to `evaluate_account_containment_eligibility` outside approved tests/policy code.
3. Integration tests prove the feature gate cannot be bypassed.
4. Verifier checks only V2-025 acceptance, not V2 Gate 4 completion.

## Verification Commands

```bash
pytest tests/contracts/ tests/policy/ -q
```
