# Implementer result — agentic-judgment-07-org-config-tool

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/agentic/tools.py` | Added `OrgConfigSectionTool` returning `OrgConfigSectionResult` (section text only; no `EvidenceFacts`; validates against `ORG_CONFIG_SNAPSHOT_HASH_KEYS`) |
| `tests/judgment/agentic/test_tools.py` | TDD tests for successful section fetch and unknown-section rejection; fixture via `preflight_path(EXAMPLE_CONFIG)` |

## Verification commands

```
PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src pytest tests/judgment/agentic/test_tools.py -v
```
**9 passed** in 0.64s (exit 0)

```
PYTHONPATH=... ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py
```
All checks passed (exit 0)

```
PYTHONPATH=... mypy src/praetor/judgment/agentic/tools.py
```
Success: no issues found in 1 source file (exit 0)

## Acceptance criteria

- **Section text only, no EvidenceFacts:** `OrgConfigSectionTool.invoke` returns `OrgConfigSectionResult` with `section_name` + `content`; no `.facts` field.
- **Not corroboration-eligible:** org-config content is static section JSON/text; never wrapped as `EvidenceFact` or tagged with a corroboration provenance path.
- **Recordable as OrgConfigCallRecord:** result fields (`section_name`, `content`, `succeeded`, `error`) map directly to `OrgConfigCallRecord` fields (verified structurally by registry Task 2; no dedicated wiring test in this task per plan).

## Gaps / notes

- Plan referenced `tests.config.conftest.minimal_org_config_snapshot` which does not exist; used `tests.config.helpers.preflight_path(EXAMPLE_CONFIG)` instead (same pattern as `tests/contracts/conftest.py`).
- No explicit test that `OrgConfigCallRecord` construction succeeds from tool result (plan Step 1 lists only two tests).
- `snapshot_hash` is excluded from `ORG_CONFIG_SNAPSHOT_HASH_KEYS` by design — requesting it returns failed result (not tested).
- Task 12 (`provider.py`) will construct `OrgConfigSectionTool` from `fetch_snapshot_by_hash`; not in scope here.
- **Not committed** per standing orders.
