# Verifier packet — agentic-judgment-06-tools-evidence

## Goal
Implement `LedgerHistoryTool` and `WiderTelemetryTool` with raw_source isolation.

## Acceptance criteria
- `LedgerHistoryTool` returns `EvidenceFact`s with `provenance_path=ledger_history` and never leaks `raw_source`.
- `WiderTelemetryTool` re-fetches untruncated facts from the request `EvidenceBundle` using existing provenance paths.
- Scope constraints from the design are enforced in tests.

## Changed files
- `src/praetor/judgment/agentic/tools.py` (new, untracked)
- `tests/judgment/agentic/test_tools.py` (new, untracked)

## Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)
- `pytest tests/judgment/agentic/test_tools.py -v`
- `ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py`
- `mypy src/praetor/judgment/agentic/tools.py`

## Focus checks (skeptic)

### 1. LEDGER_HISTORY provenance
In `src/praetor/judgment/agentic/tools.py`, confirm `_edict_to_history_fact` sets `provenance_path=LEDGER_HISTORY` (constant from `praetor.evidence.provenance`, value `"ledger_history"`).
Confirm `test_ledger_history_tool_returns_facts_for_allowed_target` asserts provenance on returned facts.

### 2. raw_source isolation (DEC-047)
**LedgerHistoryTool:** `raw_source` holds `edict.model_dump_json()`; `normalized_fields` must be a curated subset only (no full edict JSON, no `model_judgment` blob in normalized_fields). Tool must not build prompt excerpts or alternate string paths.
**WiderTelemetryTool:** Returns existing `EvidenceFact` objects unchanged (identity equality in tests). `test_wider_telemetry_tool_does_not_expose_raw_source_field_name_change` pins structural contract (raw_source remains on object; prompt exclusion is Task 12).

### 3. WiderTelemetry = untruncated bundle re-fetch (NOT wider window)
Confirm `WiderTelemetryTool` takes `facts_by_id` only — no time-window args, no re-correlation, no new provenance paths.
Default invoke `{}` returns all mapped facts; optional `evidence_ids` filters within map.
Tests must not imply a wider telemetry window.

### 4. Scope constraints
**LedgerHistoryTool:** `allowed_target_ids` enforced before query; out-of-scope `target_ids` → `ScopeViolationError`; omitted `target_ids` defaults to all allowed.
**WiderTelemetryTool:** Unknown `evidence_ids` → failed `ToolResult` with empty facts.

### 5. Boundary / untouched paths
- No changes under `src/praetor/policy/`.
- No changes to `VertexProvider` / `FakeProvider` single-shot behavior.
- Production changes confined to `files_allowed`.

## Implementer result
`.workflow/agentic-judgment-06-tools-evidence/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-06-tools-evidence/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Write `results/verifier-result.md` with PASS/BLOCK and command evidence.
