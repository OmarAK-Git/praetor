# v2-gate-2-exit — Plan

## Goal (verbatim)

V2 Gate 2 exit (PASS-only): authorization rewire sprint complete per docs/proposals/v2_implementation_plan.md § V2 Gate 2.

## Tier

T2 — phase_exit verification (PASS-only gate). No new implementation.

## Scope

Full V2 Gate 2 exit verification only. No new implementation; confirm pass
criteria for V2-011 through V2-016. Confirm the sprint-complete state, do not
introduce feature changes.

## Dependencies (all must be done)

- v2-011-host-corroboration — done
- v2-012-default-action — done
- v2-013-posture-flip — done
- v2-014-correlator-host-isolation — done
- v2-015-gate-target — done
- v2-016-fault-flag-guard — done

## Acceptance criteria

1. Host containment requires corroborated cited evidence (V2-011).
2. Default authorization posture is explicit (V2-012/V2-013).
3. No-rule targets do not contain by omission (V2-013).
4. Correlator/gate target responsibilities are enforced (V2-014, V2-015).
5. Fault flags cannot drift outside the Outcome Matrix (V2-016).
6. Full pytest, ruff, and mypy pass.

## Gate 2 pass criteria (plan § V2 Gate 2)

Host containment requires corroborated cited evidence, default authorization
posture is explicit, no-rule targets do not contain by omission,
correlator/gate target responsibilities are enforced, and fault flags cannot
drift outside the Outcome Matrix.

## Verification commands (phase_exit)

- `pytest -q`
- `ruff check .`
- `mypy .`

## Allowed files

- `.workflow/v2-gate-2-exit/`
- `memory-bank/progress.md`
- `memory-bank/activeContext.md`
- `memory-bank/tasks.md`

## Not allowed

No source or test changes. If the gate fails, do not fix here — report and
route back to the responsible V2-0xx task.
