# Workflow Plan — V2-024 Account Containment Production Enablement

## Goal

V2-024 — Account containment production enablement: account_auto_contain_enabled passes preflight only when identity gates are satisfied; corroborated SID-backed account auto_contain harness scenario passes; disabled configs still escalate account_containment_disabled.

## Scope

Account containment enablement and identity gating only. Do not run V2 Gate 4 exit.

## Tier

T2

## Allowed Files

- `src/praetor/config/preflight.py`
- `src/praetor/policy/gate.py`
- `evals/`
- `tests/config/`
- `tests/policy/`
- `tests/correlation/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`, `memory-bank/progress.md`, `memory-bank/activeContext.md`

## Acceptance Criteria

1. `account_auto_contain_enabled=true` passes preflight only when identity gates are satisfied by local deterministic tests.
2. Production account `auto_contain` harness scenario passes with SID-backed, corroborated identity.
3. Feature-disabled configs still escalate `account_containment_disabled`.
4. Verifier checks only V2-024 acceptance, not V2 Gate 4 completion.

## Verification Commands

```bash
pytest tests/config/ tests/policy/ tests/correlation/ -q
```
