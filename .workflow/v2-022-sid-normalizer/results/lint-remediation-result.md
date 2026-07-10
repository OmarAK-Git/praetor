# V2-022 — Lint remediation (Gate 3 attempt-1 fallout)

implementation_model: composer-2.5-fast (controller inline — mechanical lint only)
verification_model: full-suite fresh run (ruff/mypy/pytest at repo root)

## Why reopened

V2 Gate 3 attempt-1 FAILED on criterion 8 (`ruff check .`). Task reopened
`pending` to remediate the finding in this task's `files_allowed`.

## In-scope finding fixed

- I001 import block un-sorted — `tests/evidence/test_sid_format.py:3`
  (ruff isort reorder; no behavioral change).

## Verification (fresh, repo root, sandbox disabled)

| Check | Command | Exit | Summary |
| --- | --- | --- | --- |
| ruff | `python -m ruff check .` | 0 | All checks passed |
| mypy | `python -m mypy .` | 0 | no issues in 124 source files |
| pytest | `python -m pytest -q` | 0 | 914 passed, 2 deselected |

Original V2-022 acceptance remains satisfied (evidence: `results/verifier-result.md`).
