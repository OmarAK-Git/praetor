# Remediation Result — v2-gate-2-exit (attempt 2, user-approved scope widening)

The initial gate run FAILED criterion 6. With explicit user approval to widen
scope beyond `files_allowed`, the controller performed full remediation.

## ruff — fixed all 40 findings

- `ruff check . --fix` auto-fixed 8 (I001 import order, F401 unused imports,
  F541, UP015).
- Remaining 32 fixed manually (31 E501 line wraps + 1 F841 unused variable):
  - `src/praetor/contracts/fault_flags.py` — wrapped 2 lines.
  - `tests/policy/test_edict_fault_flags.py` — wrapped 2 `pytest.raises`,
    removed unused `bundle` var + now-unused `host_bundle` import.
  - `.claude/hooks/stop_gate.py` — wrapped 2 lines.
  - `.workflow/_dream/bin/{compaction,consolidate,dream_lib,test_compaction}.py`
    — wrapped long lines; moved one trailing comment.
  - `notebooks/praetor_walkthrough.ipynb` — wrapped 15 lines across code cells
    4 and 6 (behavior-preserving; committed outputs unaffected).
- Result: `ruff check .` → exit 0, "All checks passed!".

## mypy — resolved `mypy .` invocation (config only, no source type changes)

Root cause: `mypy .` (positional) overrides the config `packages` and scans
loose per-directory `conftest.py` files (9, no `__init__.py`) → "Duplicate
module named conftest" abort; it would also strict-check the untyped test tree
(262 errors) and external-dependency tooling never covered by the configured
`packages` scope.

Fix in `[tool.mypy]` (pyproject.toml):
- `mypy_path = "src"` + `explicit_package_bases = true` — src-layout resolves to
  `praetor.*`; per-dir conftest files get distinct qualified names.
- `exclude` for `tests/`, `tools/`, `.workflow/`, `.claude/`, `notebooks/`,
  `build/`, `awesome-ai-workflow/` — restricts the positional `.` scan to the
  real source packages, matching the configured `packages` surface.

No source type annotations were changed. Bare `mypy` still passes (123 files);
`mypy .` now passes (122 source files).

## Final gate evidence (controller runs, sandbox disabled)

| Command | Exit | Result |
| --- | --- | --- |
| `pytest -q` | 0 | 856 passed, 2 deselected |
| `ruff check .` | 0 | All checks passed |
| `mypy .` | 0 | Success: no issues found in 122 source files |

Awaiting fresh-context verifier confirmation before queue `done`.
