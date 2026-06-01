# Plan: task-001

## Goal

Establish the Python package skeleton and test harness so `pytest` runs, `praetor` imports, and a fixture manifest stub loads — satisfying **Task 1** in `docs/plan.md` and unblocking Task 2 (contracts). No Praetor business logic in this task.

## Scope

**In scope:**

- `pyproject.toml` — project metadata, `src/` layout, pytest configuration, minimal runtime/dev dependencies for smoke tests
- `src/praetor/__init__.py` — importable package (version string optional)
- `tests/test_smoke.py` — smoke import + fixture manifest load
- `tests/fixtures/README.md` — documents fixture layout for later tasks
- `tests/fixtures/fixture_manifest.yaml` — stub manifest loadable by tests

**Out of scope:**

- Pydantic contracts, `schemas/`, hashing (`docs/contracts.md` implementation — Task 3)
- Application modules under `src/praetor/` beyond `__init__.py`
- CI workflow files (not listed in Task 1)
- Changes to `docs/`, `memory-bank/` (except post-approval status updates)
- Virtualenv / lockfile policy (document in verification; not required by plan)

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| REQ-001 | `pytest` runs successfully | `docs/plan.md` Task 1 — Done when |
| REQ-002 | Package `praetor` imports | `docs/plan.md` Task 1 — Test first: smoke import |
| REQ-003 | Fixture manifest stub exists and loads | `docs/plan.md` Task 1 — Test first / Files |
| REQ-004 | File set matches plan: `pyproject.toml`, `src/praetor/__init__.py`, `tests/test_smoke.py`, `tests/fixtures/README.md`, `tests/fixtures/fixture_manifest.yaml` | `docs/plan.md` Task 1 — Files |
| REQ-005 | No dependency on Task 2+ code paths | `docs/plan.md` Task 1 — Depends on: none |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Python minimum version unspecified in docs | Wrong baseline for Pydantic v2 (Task 2) | Propose **3.11+** in implementation; confirm at review |
| `pyproject.toml` tool choices not specified | Rework if reviewer prefers setuptools vs hatchling | Use PEP 517 `hatchling` + `src` layout; document in PR |
| Fixture manifest schema undefined for Task 1 | Over-building stub | Minimal YAML (e.g. `version`, empty `fixtures: []`); Task 2+ extend |
| Windows path / line-ending issues in tests | Flaky manifest paths | Resolve manifest path relative to test file or project root |

## Task breakdown

| ID | Task | Depends on | Notes |
|----|------|------------|-------|
| T-001 | Author `pyproject.toml` (name, version, `packages`/`src` layout, `[tool.pytest.ini_options]`, optional `[project.optional-dependencies] dev`) | — | Editable install: `pip install -e ".[dev]"` |
| T-002 | Add `src/praetor/__init__.py` | T-001 | Expose `__version__` if useful for smoke test |
| T-003 | Add `tests/fixtures/fixture_manifest.yaml` stub + `tests/fixtures/README.md` | — | README points to future eval/correlation fixtures (Tasks 26+) |
| T-004 | Add `tests/test_smoke.py` | T-002, T-003 | `import praetor`; load YAML manifest; assert minimal keys |
| T-005 | Run verification suite (see `verification.md`) | T-001–T-004 | Record actual output before marking TASK-001 done |

## Verification plan (summary)

1. `pip install -e ".[dev]"` (or documented equivalent) succeeds.
2. `pytest` exits 0 with at least smoke tests collected.
3. Smoke tests: import `praetor`; load `tests/fixtures/fixture_manifest.yaml` without error.
4. No files outside Task 1 file list unless explicitly approved.

Detail and evidence slots: `.workflow/task-001/verification.md`.
