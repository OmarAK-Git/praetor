# V2-020 — Lint remediation (Gate 3 attempt-1 fallout)

implementation_model: composer-2.5-fast (controller inline — mechanical lint only)
verification_model: full-suite fresh run (ruff/mypy/pytest at repo root)

## Why reopened

V2 Gate 3 attempt-1 FAILED on criterion 8 (`ruff check .`). Task reopened
`pending` to remediate findings in this task's `files_allowed`.

## In-scope findings fixed

- I001 import block un-sorted — `src/praetor/engine/orchestrator.py:3`, including
  the duplicate-source split at lines 57-59 consolidated to a single
  `from praetor.metrics.events import (...)` block.
- E501 line too long (90 > 88) — `tests/metrics/test_metrics_completeness.py:46`
  (function signature wrapped across lines; identical parameters).

No behavioral change — import consolidation/ordering and one signature wrap only.

## Verification (fresh, repo root, sandbox disabled)

| Check | Command | Exit | Summary |
| --- | --- | --- | --- |
| ruff | `python -m ruff check .` | 0 | All checks passed |
| mypy | `python -m mypy .` | 0 | no issues in 124 source files |
| pytest | `python -m pytest -q` | 0 | 914 passed, 2 deselected |

Original V2-020 acceptance remains satisfied (evidence: `results/verifier-result.md`).
