# Orchestration — Autopilot Loop

## Dispatch policy

The controller is `.cursor/commands/gsd-autopilot-loop.md`.

For each runnable queue item:

1. The controller creates a scoped task run under `item.run_dir`.
2. The controller writes an implementation packet to `packets/implementer.md`.
3. One implementation subagent runs against that packet.
4. The controller records implementation output in `results/implementer-result.md`.
5. A separate fresh-context verifier runs against only the task goal, acceptance criteria, changed files, and task verification commands.
6. The controller records verifier output in `results/verifier-result.md`.
7. The controller updates `.workflow/autopilot-queue.json` only after verifier status is known.

## Agent roles

| Role | Agent | Model | Writes | Completion authority |
| --- | --- | --- | --- | --- |
| Controller | main Cursor agent | UI selection (orchestration only for tasks) | queue and workflow state | no task completion without verifier evidence |
| Implementer | `implementer` subagent | `defaults.implementation_model` (`composer-2.5-fast`) | task-scoped files only | none |
| Task verifier | `skeptic-verifier` subagent | `defaults.verification_model` (`claude-opus-4-8-thinking-high`) | verification artifact only | pass / block / human_needed |
| Gate verifier | current chat (no subagent) | **UI-selected Claude** in fresh Chat B | gate run dir + queue | pass / block for `phase_exit` only |

Task items: controller dispatches implementer and verifier subagents with the models above — the chat UI model does not matter for Chat A as long as the controller delegates.

Gate items (`run_mode: chat_gate`): run in a **fresh chat** with Claude selected in the UI; no subagent dispatch.

## Loop bounds

- Default behavior: drain every currently runnable `pending` or `retry` task.
- Optional cap: `--max-tasks N`.
- Default `max_retries_per_task`: 1.
- Default `allow_parallel_implementation`: false.
- Stop after any `blocked` or `human_needed` task.
- Stop when the same task-scoped verifier gap repeats for the same task.
- Stop when implementation produces an empty or irrelevant diff.
- Stop before destructive, externally visible, or permissioned setup actions.
- Stop cleanly when remaining tasks are waiting on `depends_on`.

## Approval gates

The loop must stop and ask before:

- installing dependencies
- editing `.codex` or `.claude`
- cloning GitHub repositories
- writing outside the workspace
- deployments, migrations, publishes, or external service mutations
- destructive git actions or broad resets
- widening files beyond `files_allowed`

## Queue status transitions

| From | Event | To |
| --- | --- | --- |
| `pending` | selected by controller | `in_progress` |
| `in_progress` | implementation result recorded | `verifying` |
| `verifying` | verifier passed | `done` |
| `verifying` | verifier found gaps and retry remains | `retry` |
| `retry` | selected by controller | `in_progress` |
| `verifying` | verifier found gaps and retry cap reached | `blocked` |
| `verifying` | verifier needs human check | `human_needed` |
| any runnable | approval gate or malformed result | `blocked` |

Queue items with `depends_on` are skipped until every dependency item is `done`.

## Evidence contract

A task is not done unless all of these exist:

- task `plan.md` with the original goal
- implementation packet
- implementer result
- verifier result
- queue item `status: done`
- queue item `evidence` path pointing at verifier output

Phase and sprint gates are explicit queue items. Routine packet tasks must not run full phase exit verification and must not fail because later packets are still pending.

## Packet contract

Each implementation packet must include:

- objective
- original user goal
- relevant docs and state files
- allowed files
- do-not-touch boundaries
- acceptance criteria
- verification commands
- expected result schema

Each verifier packet must include:

- original user goal
- acceptance criteria
- changed files or diff summary
- verification commands
- implementation result path
- instruction to treat implementer claims as unevidenced until checked
- instruction to ignore phase-level gaps unless the queue item sets `verification.scope` to `phase_exit` or `milestone_exit`
