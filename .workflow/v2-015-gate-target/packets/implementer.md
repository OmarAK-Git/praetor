# Implementer Packet — V2-015 Gate Target Ownership Guard

## Objective

Enforce AG-0080: intake must persist only the containment target returned by PolicyGate evaluation; orchestrator must not re-derive directive target from raw bundle facts.

## Original User Goal

V2-015 — Gate target ownership guard: intake persists only the target returned by PolicyGate evaluation; static or integration guard fails if orchestrator re-derives directive target from raw bundle facts.

## Relevant Docs and State

- `docs/proposals/v2_implementation_plan.md` § V2-015
- `.workflow/_dream/playbook.digest.md` AG-0080
- `memory-bank/activeContext.md` item 5 (PolicyGate target selection)
- `tests/policy/test_citation_anchored_host_targeting.py` (gate-level multi-host tests)

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

## Do-Not-Touch Boundaries

- Do not mark the queue item done
- Do not run phase/sprint exit verification (`pytest -q`, full ruff/mypy)
- Stop and report before: dependency installs, `.codex`/`.claude` edits, clones, writes outside allowed files
- Do not implement V2-016 fault-flag guards

## Acceptance Criteria

1. Intake persists only the target returned by PolicyGate evaluation.
2. Static or integration guard fails if orchestrator re-derives directive target from raw bundle facts.
3. Multi-host noise scenario proves uncited hosts cannot affect directive target.
4. AG-0080 enforced by tests, not convention only.

## Verification Commands

```bash
pytest tests/engine/ tests/policy/ -q
```

## Expected Result Schema

Write summary to `.workflow/v2-015-gate-target/results/implementer-result.md` with:

- Files changed
- How gate-resolved target ownership is enforced
- Test additions
- Verification command output (pass/fail)
- Any approval gates hit (should be none)

## Implementation Hints

- Add explicit `resolved_target` (or equivalent) on `PolicyGateEvaluation` set during gate evaluation.
- Orchestrator intake path should consume gate evaluation target, not call `resolve_containment_target` or rebuild from bundle facts.
- Add AST/source static guard in `tests/engine/` forbidding bundle-based target re-derivation in orchestrator.
- Add intake integration test for multi-host noise (uncited hosts cannot steer directive target).
