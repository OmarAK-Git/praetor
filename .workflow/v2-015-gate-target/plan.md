# Workflow Plan — V2-015 Gate Target Ownership Guard

## Goal

V2-015 — Gate target ownership guard: intake persists only the target returned by PolicyGate evaluation; static or integration guard fails if orchestrator re-derives directive target from raw bundle facts.

## Scope

Gate target ownership enforcement only. Do not run V2 Gate 2 exit or full-suite verification.

## Tier

T2

## Acceptance Criteria

- Intake persists only the target returned by PolicyGate evaluation.
- Static or integration guard fails if orchestrator re-derives directive target from raw bundle facts.
- Multi-host noise scenario proves uncited hosts cannot affect directive target.
- AG-0080 is enforced by tests, not only by convention.
- The verifier checks only V2-015 acceptance, not V2 Gate 2 completion.

## Allowed Files

- `src/praetor/engine/orchestrator.py`
- `src/praetor/policy/gate.py`
- `tests/engine/`
- `tests/policy/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`
- `memory-bank/progress.md`
- `memory-bank/activeContext.md`

## Verification Commands

```bash
pytest tests/engine/ tests/policy/ -q
```

## Do Not Touch

- Full pytest / ruff / mypy gate (V2 Gate 2 exit item)
- Correlator host isolation (V2-014 complete)
- Fault-flag static guards (V2-016)
