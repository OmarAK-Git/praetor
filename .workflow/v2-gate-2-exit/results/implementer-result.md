# Gate Run Result — v2-gate-2-exit (PASS-only)

Run by: test-runner subagent (fresh context), controller-dispatched.
No source or test files were modified.

## Commands and exit codes

| Command | Exit code | Status |
| --- | --- | --- |
| `pytest -q` | 0 | PASS |
| `ruff check .` | 1 | FAIL |
| `mypy .` | 2 | FAIL |

## pytest — PASS

- 856 passed, 2 deselected (~64s). No failures, errors, or unexpected xpass.

## ruff check . — FAIL (40 findings)

By rule:
- E501 line-too-long (14): `.claude/hooks/stop_gate.py:48,91`;
  `.workflow/_dream/bin/compaction.py:59,63,120,134,184`;
  `.workflow/_dream/bin/consolidate.py:117`;
  `.workflow/_dream/bin/dream_lib.py:150,669`;
  `.workflow/_dream/bin/test_compaction.py:37,90`;
  `src/praetor/contracts/fault_flags.py:144,145`;
  `tests/policy/test_edict_fault_flags.py:35,52`;
  `notebooks/praetor_walkthrough.ipynb` (6 across cells).
- I001 import-block-unsorted (4): `evals/outcome_matrix.py:7`;
  `notebooks/praetor_walkthrough.ipynb` cell 3; `src/praetor/engine/edict.py:3`;
  `tests/engine/test_gate_target_ownership.py:3`.
- F401 unused-import (2): `.workflow/_dream/bin/compaction.py:37`;
  `.workflow/_dream/bin/test_compaction.py:20` (`pathlib.Path`).
- UP015 (1): `.claude/hooks/learn_gate.py:55`.
- F541 f-string-no-placeholders (1): `.workflow/_dream/bin/test_compaction.py:67`.
- F841 unused-variable (1): `tests/policy/test_edict_fault_flags.py:64` (`bundle`).

### Classification

- Shipping V2 code/tests (owned by V2-015/V2-016): `src/praetor/contracts/fault_flags.py`,
  `src/praetor/engine/edict.py`, `evals/outcome_matrix.py`,
  `tests/engine/test_gate_target_ownership.py`, `tests/policy/test_edict_fault_flags.py`.
- Auxiliary tooling / non-shipping: `.claude/hooks/`, `.workflow/_dream/bin/`,
  `notebooks/praetor_walkthrough.ipynb`.

## mypy . — FAIL (blocked)

- error: Duplicate module named "conftest" (`tests/contracts/conftest.py` vs
  `tests/containment/conftest.py`). mypy aborts before type-checking; exit 2.
  This is an invocation/config issue (test conftest collection), not a proven
  type regression — but it means `mypy .` does not pass as required.

## Verdict

Gate 2 exit **FAILS** acceptance criterion 6. Fixing requires editing files
outside this task's `files_allowed` (source, tests, tooling, ruff/mypy config),
which is an approval gate for the autopilot loop.
