# V2-019 — Lint remediation (Gate 3 attempt-1 fallout)

implementation_model: composer-2.5-fast (controller inline — mechanical lint only)
verification_model: full-suite fresh run (ruff/mypy/pytest at repo root)

## Why reopened

V2 Gate 3 attempt-1 FAILED on criterion 8 (`ruff check .`). Task reopened
`pending` to remediate findings in this task's `files_allowed`.

## In-scope findings fixed

- I001 import block un-sorted — `src/praetor/ledger/__init__.py:3`
  (reorder `store` before `tip_anchor`).
- I001 import block un-sorted — `src/praetor/revocation/exporter.py:8`.
- E501 line too long (96 > 88) — `src/praetor/revocation/exporter.py:270`
  (`completed_at = ...` wrapped in parentheses; identical expression).

No behavioral change — import ordering and one line wrap only.

## Verification (fresh, repo root, sandbox disabled)

| Check | Command | Exit | Summary |
| --- | --- | --- | --- |
| ruff | `python -m ruff check .` | 0 | All checks passed |
| mypy | `python -m mypy .` | 0 | no issues in 124 source files |
| pytest | `python -m pytest -q` | 0 | 914 passed, 2 deselected |

Original V2-019 acceptance remains satisfied (evidence: `results/verifier-result.md`).
