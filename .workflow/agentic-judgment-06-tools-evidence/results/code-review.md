# Code review — agentic-judgment-06-tools-evidence

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 6 — `LedgerHistoryTool` and `WiderTelemetryTool`  
**Spec:** `.workflow/agentic-judgment-06-tools-evidence/plan.md`  
**Design:** `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md` (tool table, WiderTelemetry rescoping, DEC-047)

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Production | New `src/praetor/judgment/agentic/tools.py` (untracked) |
| Tests | New `tests/judgment/agentic/test_tools.py` (untracked) |
| Diff baseline | Matches Task 6 Step 3 in `docs/superpowers/plans/2026-07-30-agentic-judgment.md` verbatim |
| Tests (fresh run) | `pytest tests/judgment/agentic/test_tools.py -v` → **7 passed** in 0.63s |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |
| PolicyGate / provider | No changes outside `files_allowed` |

---

## Focus-area review

### 1. LEDGER_HISTORY provenance — PASS

`src/praetor/judgment/agentic/tools.py:51-70` — `_edict_to_history_fact` sets `provenance_path=LEDGER_HISTORY` (imported constant from `praetor.evidence.provenance`).

`tests/judgment/agentic/test_tools.py:102` — `test_ledger_history_tool_returns_facts_for_allowed_target` asserts `result.facts[0].provenance_path == LEDGER_HISTORY`.

Normalized fields are a curated subset (decision_id, alert_reference, disposition, fault_flags, optional target_type/target_id) — not attacker-controllable log paths.

### 2. raw_source isolation (DEC-047) — PASS

**LedgerHistoryTool:** Full edict JSON is stored only in `EvidenceFact.raw_source` (`tools.py:66`); `normalized_fields` excludes it (`tools.py:53-64`). This matches the existing contract pattern (`excerpt.py` strips `_RAW_SOURCE_KEY` at the prompt boundary). No stringified excerpt or alternate field path is introduced.

**WiderTelemetryTool:** Returns existing `EvidenceFact` instances unchanged (`tools.py:116-122`); no re-serialization or excerpt construction.

`tests/judgment/agentic/test_tools.py:168-178` — structural guard pins that `raw_source` remains on the contract object (prompt exclusion deferred to Task 12 per plan).

**Gap (non-blocking):** Design spec calls for DEC-047 isolation tests extending to *each* evidence-producing tool; Task 6 plan prescribes only the WiderTelemetry structural test. No ledger-specific assertion that `normalized_fields` never contains edict JSON.

### 3. WiderTelemetry untruncated re-fetch (not wider window) — PASS

`WiderTelemetryTool` is constructed with `facts_by_id: Mapping[str, EvidenceFact]` — the correlated bundle slice only (`tools.py:101-107`). No time-window parameters, no re-correlation, no new provenance paths.

- Default `{}` → all bundle facts (`tools.py:115-116`, tested `test_tools.py:146-151`)
- Optional `evidence_ids` filter → same objects by ID (`tools.py:121-122`, tested `test_tools.py:154-158`)
- Unknown IDs → failed `ToolResult`, no partial leak (`tools.py:117-121`, tested `test_tools.py:161-165`)

Identity equality (`assert result.facts == (fact,)`) proves untruncated re-fetch: the tool does not apply `MAX_PROMPT_EXCERPT_CHARS` head-tail truncation.

### 4. Scope constraints — PASS

**LedgerHistoryTool** (`tools.py:74-98`):

- `allowed_target_ids` frozen at construction (alert host/account scope)
- Any requested `target_ids` outside allowed set → `ScopeViolationError` (`tools.py:89-92`, tested `test_tools.py:106-115`)
- Omitted `target_ids` → defaults to all allowed targets (`tools.py:93`, tested `test_tools.py:118-131`)
- Scope checked *before* `fetch_edicts_for_target_history` — no SQL widening from out-of-scope IDs

**WiderTelemetryTool:** Scope is the injected `facts_by_id` map; unknown `evidence_ids` rejected (tested). No path to fetch facts outside the bundle.

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/judgment/agentic/test_tools.py`** — No ledger-specific DEC-047 isolation test (e.g. assert `raw_source` populated and `normalized_fields` does not contain edict JSON keys like `model_judgment`). Plan Step 1 does not require it; design spec's "each tool" wording is broader.

2. **`tests/judgment/agentic/test_tools.py`** — Invalid `target_ids` / `evidence_ids` type handling (`tools.py:85-88`, `111-114`) returns failed `ToolResult` but is untested.

3. **`tests/judgment/agentic/test_tools.py`** — No test for mixed in-scope/out-of-scope `target_ids` in one call (implementation correctly fails closed on any unknown).

4. **`tests/judgment/agentic/test_tools.py:168`** — Test name `test_wider_telemetry_tool_does_not_expose_raw_source_field_name_change` is misleading; it asserts `raw_source` *is* present on the returned fact (structural contract guard), not that it was stripped.

5. **`tests/judgment/agentic/test_tools.py`** — Untruncated re-fetch is implied by object identity, not by asserting full `normalized_fields` length (e.g. 500-char `command_line` in `_wider_fact`).

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| LedgerHistoryTool returns `EvidenceFact`s with `provenance_path=ledger_history` | Met |
| LedgerHistoryTool never leaks `raw_source` (prompt-layer isolation) | Met structurally — `raw_source` on contract only; curated `normalized_fields`; no excerpt path |
| WiderTelemetryTool re-fetches untruncated facts from correlated bundle with existing provenance paths | Met — same `EvidenceFact` objects, no window/re-correlation |
| Scope constraints enforced in tests | Met — ledger scope + wider unknown-ID rejection |
| Files allowed only | Met — only `tools.py`, `test_tools.py`, workflow artifacts |
| PolicyGate / single-shot provider untouched | Met — no diffs in those paths |
| Verification commands pass | Met — fresh 7/7 pytest, ruff, mypy |

---

## Correctness / security / simplicity

- **Correctness:** `LedgerHistoryTool` delegates to Task 5 `fetch_edicts_for_target_history` with construction-time `alert_reference` and scope-filtered `target_ids`. `WiderTelemetryTool` preserves request order for filtered IDs.
- **Security:** Out-of-scope ledger targets raise before DB query. Wider telemetry cannot escape bundle map. Parameterized ledger query remains in `store.py` (Task 5).
- **Simplicity:** Implementation matches prescribed plan code; stub `OrgConfigSectionResult` / `ExemplarToolResult` included per plan for Tasks 7–8. No duplicate tool helpers elsewhere.

---

## Summary

Task 6 implementation matches the approved plan and design rescoping for WiderTelemetry (bundle re-fetch, not wider time window). LEDGER_HISTORY provenance, DEC-047 structural isolation, and scope enforcement are correctly implemented. Minor test gaps do not block verification. Proceed to skeptic verification.
