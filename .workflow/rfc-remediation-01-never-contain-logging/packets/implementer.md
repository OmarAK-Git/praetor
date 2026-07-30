# Implementer Packet

Implement Task 1 from `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md` using test-driven development.

Objective: add warning visibility to both existing `PreflightError` skip branches in `praetor.config.live`.

Read first:
- `.workflow/rfc-remediation-01-never-contain-logging/plan.md`
- The Task 1 section of the source plan
- `.workflow/_dream/playbook.digest.md`

Boundaries:
- Modify only `src/praetor/config/live.py` and `tests/config/test_live_never_contain_matching.py`, plus the result artifact and exact task commit.
- Preserve all return values and skip/continue behavior.
- Do not alter PolicyGate, disposition logic, DEC-053 ordering, or validation semantics.
- Do not stage or modify unrelated pre-existing working-tree files.
- Do not mark the queue item done.
- Stop and report before dependency installs, `.codex`/`.claude` edits, clones, external writes, destructive Git, or scope expansion.

Required flow:
1. Add the focused failing tests and run them to demonstrate the expected red state.
2. Implement the module logger and warning calls.
3. Run the focused test, `ruff check .`, and `mypy .`.
4. Self-review the diff.
5. Commit only the two allowed implementation/test paths with the source plan's Task 1 commit message.
6. Write `.workflow/rfc-remediation-01-never-contain-logging/results/implementer-result.md` with model, changed files, red/green evidence, verification outputs, commit hash, and concerns.

Return only: status (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`), commit hash, one-line verification summary, and concerns.
