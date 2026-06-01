# Traceability: task-001

Map requirements → implementation steps → code → verification. Code artifacts empty until implementation approved.

| Req ID | Requirement (summary) | Task ID | Code / artifact | Verification |
|--------|-------------------------|---------|-----------------|----------------|
| REQ-001 | `pytest` runs | T-001, T-005 | `pyproject.toml` | V-001 |
| REQ-002 | Package imports | T-002, T-004 | `src/praetor/__init__.py`, `tests/test_smoke.py` | V-002 |
| REQ-003 | Fixture manifest loads | T-003, T-004 | `tests/fixtures/fixture_manifest.yaml`, `tests/test_smoke.py` | V-003 |
| REQ-004 | Planned file set present | T-001–T-004 | All Task 1 paths in `docs/plan.md` | V-004 |
| REQ-005 | No Task 2+ dependencies | T-001–T-004 | (no `src/praetor/contracts/` etc.) | V-005 |

## Orphan / unmapped

- Requirements with no task: none
- Tasks with no requirement: none
- Code changes with no verification: none (pending implementation)
