# Autopilot Loop Setup — Praetor

## Goal

Bounded GSD autopilot loop for Praetor V2 delivery: task state in files, implementation subagent per queued task, fresh-context verification before marking done.

## Success criteria

- Cursor command `/gsd-autopilot-loop` exists.
- Queue schema at `.workflow/autopilot-queue.json` with `depends_on`, task-scoped verification default, and explicit phase gate items.
- Loop state under `.workflow/autopilot-loop/`.
- Implementer and verifier artifacts required before `done`.
- Stop conditions cover approval gates, empty diffs, repeated failures, and dependency-waiting.

## Constraints

- Do not install dependencies.
- Do not edit global harness config.
- Do not clone repositories or write outside the workspace.
- Phase/sprint gates are explicit queue items only (`verification.scope: phase_exit`).

## Work packets

| ID | Objective | Status |
| --- | --- | --- |
| 01-loop-command | Add `.cursor/commands/gsd-autopilot-loop.md` | done |
| 02-queue-contract | Add queue JSON and task template | done |
| 03-run-state | Add loop orchestration and state | done |
| 04-seed-queue | Seed V2-015+ runnable chain | done |

## Verification

| ID | Check | Command | Expected |
| --- | --- | --- | --- |
| VERIFY-AUTO-001 | Queue JSON | `python -m json.tool .workflow/autopilot-queue.json` | pass |
| VERIFY-AUTO-002 | Command wiring | command references `autopilot-queue` and `autopilot-loop/state` | pass |
| VERIFY-AUTO-003 | Task-scoped default | queue `defaults.verification_scope` is `task` | pass |
| VERIFY-AUTO-004 | Gate item explicit | `v2-gate-2-exit` uses `phase_exit` scope | pass |
