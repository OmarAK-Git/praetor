# Autopilot Task Template

Copy the JSON object below into `.workflow/autopilot-queue.json` under `items`.

```json
{
  "id": "v2-015-short-slug",
  "status": "pending",
  "tier": "T2",
  "depends_on": [],
  "goal": "Copy the user goal verbatim when possible.",
  "scope": "Describe the allowed work boundary.",
  "files_allowed": [
    "src/",
    "tests/"
  ],
  "acceptance_criteria": [
    "The requested behavior is implemented.",
    "Task-scoped tests or checks pass."
  ],
  "verification": {
    "scope": "task",
    "commands": [
      "pytest tests/path/to/test_module.py -q"
    ],
    "manual_checks": []
  },
  "implementation_agent": "gsd-executor",
  "verification_agent": "gsd-verifier",
  "run_dir": ".workflow/v2-015-short-slug",
  "attempts": 0,
  "max_retries": 1,
  "evidence": []
}
```

## Rules

- Keep task IDs unique and slug-safe.
- Use `pending` for work the loop may pick up.
- Use `depends_on` when a task must wait for earlier queue items.
- Use `blocked` for tasks that require approval, secrets, dependency installs, or scope decisions.
- Use `files_allowed` to keep implementation agents from widening the task.
- Keep `verification.scope` as `task` for normal packet work.
- Use `phase_exit` only for an explicit sprint/phase gate queue item (e.g. `v2-gate-2-exit`).
- Keep verification commands deterministic and task-scoped. Prefer targeted `pytest` paths over full-suite runs for routine tasks.
- Sprint gates are **never** implied by completing the last task in a sprint — add a dedicated gate item.

## Phase exit item example

```json
{
  "id": "v2-gate-2-exit",
  "status": "pending",
  "tier": "T2",
  "depends_on": ["v2-015-gate-target", "v2-016-fault-flag-guard"],
  "goal": "V2 Gate 2 exit (PASS-only): authorization rewire sprint complete per v2_implementation_plan.md.",
  "scope": "Full Gate 2 exit verification only. No new implementation.",
  "files_allowed": [
    ".workflow/v2-gate-2-exit/",
    "memory-bank/progress.md",
    "memory-bank/activeContext.md"
  ],
  "acceptance_criteria": [
    "V2-011 through V2-016 acceptance criteria are met.",
    "Gate 2 pass criteria from docs/proposals/v2_implementation_plan.md are evidenced.",
    "Full pytest, ruff, and mypy pass."
  ],
  "verification": {
    "scope": "phase_exit",
    "commands": [
      "pytest -q",
      "ruff check .",
      "mypy ."
    ],
    "manual_checks": []
  },
  "implementation_agent": "gsd-verifier",
  "verification_agent": "gsd-verifier",
  "run_dir": ".workflow/v2-gate-2-exit",
  "attempts": 0,
  "max_retries": 1,
  "evidence": []
}
```
