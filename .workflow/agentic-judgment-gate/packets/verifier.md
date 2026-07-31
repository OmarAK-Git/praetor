# Verifier packet — agentic-judgment-gate

## Goal
Verify the complete agentic-judgment plan with repository-wide test, lint, and typecheck gates.

## Acceptance criteria
- Full pytest suite passes.
- Repository-wide ruff and mypy (src evals consumer_sdk) pass.
- All 14 task verifier artifacts exist.
- PolicyGate evaluation logic under src/praetor/policy/ shows zero diffs vs merge base for evaluation semantics (no gate logic edits).
- Single-shot FakeProvider/VertexProvider paths remain intact.
- ledger_history is the only new corroboration-eligible provenance path.

## Commands (PYTHONPATH=worktree/src)
- pytest -q
- ruff check src tests evals consumer_sdk
- mypy src evals consumer_sdk
- python tools/schema_export.py --check

## Manual checks
- Confirm PolicyGate evaluation logic untouched and single-shot path intact.
- Confirm ledger_history is the only new corroboration-eligible provenance path.

## Scope
phase_exit — full gate allowed.

Treat implementer claims as unevidenced. Write results/verifier-result.md and results/gate-commands.md.
