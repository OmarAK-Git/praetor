# Implementer Packet

Implement Task 2 from `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md` with TDD.

Read first:
- `.workflow/rfc-remediation-02-correlation-metric/plan.md`
- Source plan Task 2
- `.workflow/_dream/playbook.digest.md` metrics/correlation rules

Implement the exact additive metric field, collector method, optional correlator parameter, unsupported-event increments for both telemetry families, and orchestrator wiring. Match current repository signatures and fixture styles rather than blindly copying stale names.

Boundaries:
- Modify only the six allowed paths, plus the result artifact and exact task commit.
- Preserve correlation result contents, filtering, sorting, dispositions, PolicyGate behavior, and DEC-053 ordering.
- `MetricsCollector` remains single-writer/thread-unsafe; add no locking.
- Add no Outcome Matrix fault flag.
- Do not stage unrelated pre-existing changes or edit the queue.
- Stop for any approval gate or scope expansion.

Required flow:
1. Demonstrate red metrics-layer and correlation-wiring tests.
2. Implement in small steps and run the focused tests after each step.
3. Run the engine intake suite, `ruff check .`, and `mypy .`.
4. Self-review and commit only allowed implementation/test files using the source plan's Task 2 commit message.
5. Write `.workflow/rfc-remediation-02-correlation-metric/results/implementer-result.md` with model, changed files, red/green evidence, checks, commit, and concerns.

Return only status, commit hash, one-line verification summary, and concerns.
