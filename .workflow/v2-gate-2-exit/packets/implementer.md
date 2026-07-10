# Implementation Packet — v2-gate-2-exit (PASS-only gate run)

## Objective

Run the full V2 Gate 2 exit verification suite and capture real evidence. This
is a PASS-only phase gate: **no new implementation**. If any check fails, stop
and report; do not fix source or tests in this task.

## Original user goal

V2 Gate 2 exit (PASS-only): authorization rewire sprint complete per
docs/proposals/v2_implementation_plan.md § V2 Gate 2.

## Relevant docs and state

- `docs/proposals/v2_implementation_plan.md` § V2 Gate 2
- `.workflow/v2-gate-2-exit/plan.md`
- `memory-bank/activeContext.md`

## Allowed files

- `.workflow/v2-gate-2-exit/`
- `memory-bank/progress.md`, `memory-bank/activeContext.md`, `memory-bank/tasks.md`

## Do-not-touch

- No source (`src/`) or test (`tests/`) changes.
- No dependency installs, no config edits.

## Acceptance criteria

1. Host containment requires corroborated cited evidence (V2-011).
2. Default authorization posture is explicit (V2-012/V2-013).
3. No-rule targets do not contain by omission (V2-013).
4. Correlator/gate target responsibilities are enforced (V2-014, V2-015).
5. Fault flags cannot drift outside the Outcome Matrix (V2-016).
6. Full `pytest`, `ruff`, and `mypy` pass.

## Verification commands

- `pytest -q`
- `ruff check .`
- `mypy .`

## Expected result schema

Record in `results/implementer-result.md`: each command, exit status, summary
counts (tests passed/failed, ruff findings, mypy errors), and a PASS/FAIL
verdict per acceptance criterion with evidence.
