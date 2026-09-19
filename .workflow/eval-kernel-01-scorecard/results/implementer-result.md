# Implementer result — eval-kernel-01-scorecard (Task 1)

## Status

**implemented**

## Files created/changed

| File | Change |
|---|---|
| `evals/schemas/scorecard_schema.json` | Created — JSON Schema for scorecard row with `additionalProperties: false` and spec §4 required fields |
| `evals/scorecard.py` | Created — `ScorecardRow` Pydantic model, `validate_scorecard_row()`, pending/failure_class honesty rules |
| `tests/evals/test_scorecard.py` | Created — 6 unit tests for schema, extra=forbid, pending legality, failure_class rules |

## Commands run

| Command | Exit code | Result |
|---|---|---|
| `pytest tests/evals/test_scorecard.py -v` (pre-impl) | 2 | Expected `ModuleNotFoundError: No module named 'evals.scorecard'` |
| `pytest tests/evals/test_scorecard.py -q` | 0 | 6 passed |
| `ruff check evals/scorecard.py tests/evals/test_scorecard.py` | 0 | All checks passed (after auto-fix of import order in test file) |
| `mypy evals/scorecard.py` | 0 | Success: no issues found |
| `git commit -m "feat(evals): add E2E scorecard schema and pending rules"` | 0 | Committed 3 files |
| `git push` | 0 | Pushed to `origin/eval-kernel-sprint1` |

## Commit SHA

`204c0d4`

## Blockers

None.

## Self-review (Global Constraints)

- Task scope limited to scorecard schema + model; no kernel runner, scenarios, CI, or `src/praetor/` changes.
- `pending` restricted to `CAPABILITY_QUALITY_IDS` × `new_build` only.
- `failure_class` enforced: `none` on pass/pending; required non-`none` on fail/error.
- `ScorecardRow` uses `extra="forbid"`.
- No judgment-quality claims, Path B imports, envelope/CBC work, or Sprint 2/3 scope.

## Notes

- Queue item status **not** marked done (per instructions).
- Ruff `--fix` reordered imports in `tests/evals/test_scorecard.py` (isort: `evals.scorecard` before `pydantic`); no test logic changed.
