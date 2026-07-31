# Implementer result — agentic-judgment-11-phase1

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/agentic/phases.py` | **Created.** Phase 1 source fan-out driver with per-source `BudgetTracker`, concurrent `ThreadPoolExecutor`, and deterministic registry append order. |
| `tests/judgment/agentic/test_phases.py` | **Created.** Four focused Phase 1 unit tests (happy path, all-failed, partial failure, budget enforcement). |

## Verification commands and outcomes

```text
$ PYTHONPATH=.../src pytest tests/judgment/agentic/test_phases.py -v
4 passed in 0.28s

$ ruff check src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py
All checks passed!

$ mypy src/praetor/judgment/agentic/phases.py
Success: no issues found in 1 source file
```

## API surface for Task 12

### Dataclass

- `SourceFanoutResult` — fields: `ledger_history_succeeded`, `org_config_succeeded`, `similar_cases_succeeded`, `wider_telemetry_succeeded`; property `all_failed`.

### Public functions

- `run_source_fanout(*, ledger_model, ledger_tool, org_config_model, org_config_tool, similar_case_model, similar_case_tool, wider_telemetry_model, wider_telemetry_tool, budget, registry) -> SourceFanoutResult`
- `run_ledger_history_source(*, model, tool, budget) -> tuple[bool, list[ToolCallRecord]]`
- `run_org_config_source(*, model, tool, budget) -> tuple[bool, list[OrgConfigCallRecord]]`
- `run_similar_case_source(*, model, tool, budget) -> tuple[bool, list[ExemplarCallRecord]]`
- `run_wider_telemetry_source(*, model, tool, budget) -> tuple[bool, list[ToolCallRecord]]`

### Private helpers (module-internal)

- `_drive_investigation(model, budget, invoke) -> list[tuple[dict, bool, T]]`
- `_run_evidence_source(*, source, model, tool, budget) -> tuple[bool, list[ToolCallRecord]]`

## Gaps / deviations from plan

1. **`_StubTool.name`** — Added `name = "stub"` class attribute so stub tools satisfy `tool.name` used when building call records (plan stubs omitted this; required for tests to run).
2. **`wider_telemetry` call plan in happy-path test** — Changed from `call_plan=()` to `call_plan=({},)` so the source makes one successful tool call; with empty plan, `any(...)` over zero records is `False` and contradicts the test's `wider_telemetry_succeeded is True` assertion while preserving Task 13 all-failed semantics (zero calls = not succeeded).
3. **`phases.py` typing** — Added `TypeVar("_T")` to `_drive_investigation` and distinct loop variable names in `run_source_fanout` for strict mypy (behavior unchanged).
4. **Line wrapping** — Test file wrapped for ruff E501; logic unchanged.

## Unresolved

None. No commit made per standing orders.
