# Implementer Packet — V2-025 All Containment Through PolicyGate

**implementation_model:** composer-2.5-fast

## Objective

Enforce that all production containment authorization flows through PolicyGate — no direct calls to lower eligibility helpers that bypass `account_containment_disabled` and other gate checks.

## Original User Goal

V2-025 — All containment through PolicyGate: no production caller authorizes account or host containment via lower eligibility helpers; static guard catches direct calls; integration tests prove the feature gate cannot be bypassed.

## Relevant Docs

- `docs/proposals/v2_implementation_plan.md` § V2-025
- PE-0014: direct `evaluate_account_containment_eligibility` bypasses feature gate
- V2-024 complete: account containment enablement behind preflight identity gates

## Allowed Files

- `src/praetor/policy/identity.py`
- `src/praetor/policy/gate.py`
- `tests/contracts/`
- `tests/policy/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`, `memory-bank/progress.md`, `memory-bank/activeContext.md`

## Do-Not-Touch

- Do not mark queue item done
- Do not run V2 Gate 4 exit
- Do not install dependencies or edit global harness config
- Stop and report approval gates

## Acceptance Criteria

1. No production caller authorizes account or host containment by calling lower eligibility helpers directly.
2. Static grep/AST guard catches direct calls to `evaluate_account_containment_eligibility` outside approved tests/policy code.
3. Integration tests prove the feature gate cannot be bypassed.
4. Verifier checks only V2-025 acceptance, not V2 Gate 4 completion.

## Verification Commands

```bash
pytest tests/contracts/ tests/policy/ -q
```

Write result to `.workflow/v2-025-policygate-boundary/results/implementer-result.md`
