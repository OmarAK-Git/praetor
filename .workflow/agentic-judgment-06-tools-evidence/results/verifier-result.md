# Verifier result — agentic-judgment-06-tools-evidence

**Verdict:** PASS (claim survives)
**Role:** skeptic-verifier (fresh context; implementer transcript treated as unevidenced)

## Claim under test

Task 6 implements `LedgerHistoryTool` and `WiderTelemetryTool` such that:

1. Ledger history facts use `provenance_path=ledger_history` and keep full edict JSON only in `raw_source` (curated `normalized_fields`; no prompt-excerpt path).
2. Wider telemetry re-fetches untruncated facts from the request bundle map (not a wider time window; existing provenance paths).
3. Scope constraints are enforced in tests.
4. Production changes for this task stay in `files_allowed`; PolicyGate / single-shot providers untouched by this task.

## Fresh command evidence

Working directory: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`  
`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`

| Command | Result |
|---------|--------|
| `pytest tests/judgment/agentic/test_tools.py -v` | **7 passed** in 0.62s (exit 0) |
| `ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py` | All checks passed (exit 0) |
| `mypy src/praetor/judgment/agentic/tools.py` | Success: no issues found in 1 source file (exit 0) |

## Focus-check evidence

### 1. LEDGER_HISTORY provenance — PASS

- `praetor.evidence.provenance.LEDGER_HISTORY == "ledger_history"` (runtime assert).
- `tools.py:51-70` `_edict_to_history_fact` sets `provenance_path=LEDGER_HISTORY`.
- `test_tools.py:102-103` asserts `result.facts[0].provenance_path == LEDGER_HISTORY`.

### 2. raw_source isolation (DEC-047) — PASS (structural)

**LedgerHistoryTool** (`tools.py:51-70`):

- `raw_source=edict.model_dump_json()` only.
- `normalized_fields` curated keys only: `decision_id`, `alert_reference`, `final_disposition`, `fault_flags`, optional `target_type`/`target_id`.
- No prompt excerpt / alternate string path constructed.

Independent runtime probe (not in suite): secret `model_judgment` narrative present in `raw_source`, absent from `str(normalized_fields)`; `nf_keys == ['alert_reference', 'decision_id', 'fault_flags', 'final_disposition', 'target_id', 'target_type']`.

**WiderTelemetryTool** (`tools.py:101-123`): returns mapped `EvidenceFact` objects unchanged; no re-serialization.

`test_tools.py:168-178` pins `raw_source` remains on the returned contract object (prompt exclusion deferred to Task 12 per plan).

### 3. WiderTelemetry = untruncated bundle re-fetch — PASS

- Constructor takes `facts_by_id` only — no time-window / re-correlation args (`tools.py:101-107`).
- Default `{}` → all mapped facts; optional `evidence_ids` filters within map.
- Existing provenance preserved (same objects / same fields).
- Independent probe: `result.facts[0] is fact` is `True` (implementation identity). Suite uses value `==`, which still fails if fields were truncated (confirmed: value-equal copies compare equal; truncated copies do not).

Tests do not imply a wider telemetry window.

### 4. Scope constraints — PASS

| Behavior | Code | Test |
|----------|------|------|
| Out-of-scope `target_ids` → `ScopeViolationError` before query | `tools.py:89-92` | `test_ledger_history_tool_rejects_out_of_scope_target` |
| Omitted `target_ids` → all allowed | `tools.py:93` | `test_ledger_history_tool_defaults_to_all_allowed_targets` |
| Unknown `evidence_ids` → failed `ToolResult`, empty facts | `tools.py:117-121` | `test_wider_telemetry_tool_reports_unknown_evidence_id` |

### 5. Boundary / untouched paths — PASS (this task)

- Task deliverables untracked only: `src/praetor/judgment/agentic/tools.py`, `tests/judgment/agentic/test_tools.py`, `.workflow/agentic-judgment-06-tools-evidence/`.
- `src/praetor/policy/gate.py`, `vertex_provider.py`, `fake_provider.py`: working-tree content equal to HEAD (status ` M` is line-ending noise).
- `src/praetor/judgment/provider.py` has a prior-task `evidence_bundle` field (+4 lines) — **not** introduced by Task 6; outside this task's `files_allowed` delta.

## Acceptance criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| LedgerHistoryTool → `EvidenceFact`s with `provenance_path=ledger_history` | Met | Code + `test_ledger_history_tool_returns_facts_for_allowed_target` |
| Never leaks `raw_source` (DEC-047 structural) | Met | Curated `normalized_fields`; full dump only in `raw_source`; no excerpt path; runtime probe |
| WiderTelemetryTool re-fetches untruncated bundle facts / existing provenance | Met | Map-only API; value/`is` identity; filters within map |
| Scope constraints enforced in tests | Met | 3 scope/unknown-ID tests above |
| Verification commands pass | Met | Fresh 7/7 pytest, ruff, mypy |

## Gaps (non-blocking)

1. **No ledger-specific DEC-047 unit assertion** that `normalized_fields` excludes `model_judgment` / edict JSON (design “each tool” wording broader than Task 6 plan Step 1). Runtime probe confirms isolation; suite does not pin it.
2. **Suite uses `==` not `is`** for WiderTelemetry — code-review claim of “identity equality” overstates the test; implementation does preserve identity (verified separately). Value equality still detects truncation of the 500-char `command_line`.
3. **Invalid `target_ids` / `evidence_ids` types** return failed `ToolResult` (`tools.py:85-88`, `111-114`) — untested.
4. **Mixed in-scope + out-of-scope `target_ids`** in one call — untested (implementation fails closed on any unknown).
5. **Misleading test name** `test_wider_telemetry_tool_does_not_expose_raw_source_field_name_change` asserts `raw_source` *is* present (structural guard), not stripped.
6. **Prompt-boundary exclusion of `raw_source`** deferred to Task 12 (acknowledged by plan / implementer / review).

## Strongest reason claim survives

Independent fresh pytest/ruff/mypy are green, and direct reads plus a runtime isolation probe confirm LEDGER_HISTORY provenance, curated `normalized_fields` (no `model_judgment` leak), map-only WiderTelemetry without window semantics, and scope enforcement tested — without relying on the implementer transcript.
