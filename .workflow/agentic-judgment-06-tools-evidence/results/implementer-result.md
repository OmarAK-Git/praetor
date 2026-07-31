# Implementer result — agentic-judgment-06-tools-evidence

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/agentic/tools.py` | New module: `ToolResult`, `ScopeViolationError`, `LedgerHistoryTool`, `WiderTelemetryTool`, plus stub result types for Tasks 7–8 |
| `tests/judgment/agentic/test_tools.py` | TDD unit tests for ledger history scope enforcement, wider-telemetry re-fetch, and DEC-047 structural isolation |

## Implementation summary

- **LedgerHistoryTool** queries `fetch_edicts_for_target_history`, converts edicts to `EvidenceFact` with `provenance_path=LEDGER_HISTORY`, enforces `allowed_target_ids` scope (raises `ScopeViolationError` on out-of-scope targets), defaults to all allowed targets when `target_ids` omitted.
- **WiderTelemetryTool** re-fetches untruncated facts from the correlated bundle's `facts_by_id` map (not a wider time window); supports optional `evidence_ids` filter; reports unknown IDs as failed `ToolResult`.
- **raw_source isolation (DEC-047)**: ledger facts store edict JSON in `raw_source` (prompt layer excludes it); wider-telemetry returns existing `EvidenceFact` objects unchanged — structural guard test pins no new stringified excerpt path.

## Verification commands

```
PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src pytest tests/judgment/agentic/test_tools.py -v
```
**Result:** 7 passed in 0.62s

```
PYTHONPATH=... ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py
```
**Result:** All checks passed!

```
PYTHONPATH=... mypy src/praetor/judgment/agentic/tools.py
```
**Result:** Success: no issues found in 1 source file (run from worktree root with PYTHONPATH set)

## TDD evidence

1. Tests written first → `ModuleNotFoundError: No module named 'praetor.judgment.agentic.tools'`
2. Implementation added → 7/7 tests pass

## Gaps / notes

- No commit (per standing orders).
- `OrgConfigSectionResult` and `ExemplarToolResult` stub dataclasses included per plan so Tasks 7–8 can append to the same file.
- End-to-end prompt-boundary `raw_source` exclusion deferred to Task 12 per plan.
