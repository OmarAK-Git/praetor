# Workflow Plan — V2 Gate 4 Exit

## Goal

V2 Gate 4 exit (PASS-only): feature enablement and operator readiness sprint complete per docs/proposals/v2_implementation_plan.md § V2 Gate 4.

## Scope

Full V2 Gate 4 exit verification only. No new implementation; confirm pass criteria for V2-024 through V2-031.

## Allowed files

- `.workflow/v2-gate-4-exit/`
- `memory-bank/progress.md`
- `memory-bank/activeContext.md`
- `memory-bank/tasks.md`

## Acceptance criteria

1. Account containment can be deliberately enabled through preflight (V2-024).
2. All production containment authorization flows through PolicyGate (V2-025).
3. Org-config rate ceilings are implemented or intentionally waived (V2-026).
4. Sweep has an operator CLI (V2-027).
5. Provider integration is real but deterministic CI remains stable (V2-028).
6. Splunk demo conditions are resolved (V2-029).
7. Benchmark/operator docs are pinned (V2-030, V2-031).
8. Full pytest, ruff, and mypy pass.

## Verification commands

```bash
pytest -q
ruff check .
mypy .
```

## Tier

T2 — `verification.scope: phase_exit`, `run_mode: chat_gate`
