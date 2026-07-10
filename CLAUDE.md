# Agent Autopilot

This repo uses the `ultimate-agentic-workflow` skill for non-trivial AI coding work.

## Project

- Name: Praetor
- Source: src
- Tests: tests

## Commands

- Build: `python -m build`
- Run: `python -m <module>`
- Test: `pytest`
- Lint: `ruff check .`
- Typecheck: `mypy .`

## Workflow

Classify work before starting:

- T0: answer or tiny safe edit directly
- T1: write a one-line goal note, execute, verify
- T2: spec and plan before implementation
- T3: full traceability workflow with `.workflow/`, risk gates, verification ledger, review, reflection, and archive

Use `ultimate-agentic-workflow` for T2/T3 work, repo initialization, traceability, subagent orchestration, or autonomous loops.

Rules that apply at every tier:

- Keep live task state in a durable file, not only in conversation; it must survive context compaction.
- Do not claim completion without fresh verification evidence.
- For T2+ work, prefer review from a fresh context over self-review.

## Permissioned Setup

Before installing dependencies, editing `.codex` / `.claude` (or your harness's config directory), cloning GitHub repos, or writing outside the workspace, ask for user approval with exact commands, target paths, network/data risks, and rollback.

Keep this file short. Operational notes belong in `OPS.md`; active task status belongs in the plan or `.workflow/`.
