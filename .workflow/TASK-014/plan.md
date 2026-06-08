# Workflow Plan: TASK-014

## Goal

Implement prompt construction and excerpt hygiene for the judgment provider path so provider-facing evidence content is limited to a sanitized `PromptExcerptSet`, while preserving full verbatim org-config context and structured-output instructions.

## Scope

### In scope

- Add prompt excerpt construction for evidence facts with stable evidence IDs.
- Cap excerpt text at 200 Unicode characters.
- Use `[...omitting N characters]` when truncating.
- Use head+tail truncation for high-risk unbounded evidence fields.
- Mark incomplete excerpts so the model is told when content was truncated.
- Exclude `raw_source` from all prompt output.
- Render the active org config verbatim in the provider request after enforcing `HARD_CONFIG_CHARACTER_BUDGET`.
- Add structured-output schema instructions to the prompt payload.
- Wire the walking-skeleton provider request to use sanitized prompt output.

### Out of scope

- Do not implement Task 15 evidence citation validator changes.
- Do not implement PolicyGate or any Task 17+ gates.
- Do not modify `docs/`.
- Do not change provider-health breaker behavior, live Vertex calls, or eval harness tasks.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Every provider-facing prompt fact has a stable evidence ID. |
| REQ-002 | Prompt excerpts are capped at 200 Unicode characters. |
| REQ-003 | Truncated excerpts use the exact marker format `[...omitting N characters]`. |
| REQ-004 | High-risk unbounded fields use head+tail truncation. |
| REQ-005 | Prompt output tells the model when excerpt content is incomplete. |
| REQ-006 | `raw_source` is absent from all prompt output. |
| REQ-007 | Full org config is rendered verbatim, with character budget enforced before provider call. |
| REQ-008 | Structured-output schema instructions are present in the provider-facing prompt payload. |
| REQ-009 | `PromptExcerptSet` is the sole provider-facing evidence content. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Tests assert all prompt facts expose `evidence_id` values copied from source facts. |
| AC-002 | REQ-002 | Tests assert all excerpt text lengths are `<= 200` code points. |
| AC-003 | REQ-003 | Tests assert omitted character counts are reflected in the exact marker string. |
| AC-004 | REQ-004 | Tests assert unbounded/high-risk fields keep both leading and trailing content when truncated. |
| AC-005 | REQ-005 | Tests assert truncated excerpts carry an incomplete flag and the prompt contains an incomplete-content warning. |
| AC-006 | REQ-006 | Tests assert `raw_source` does not appear in serialized prompt payloads. |
| AC-007 | REQ-007 | Tests assert verbatim config text is present, over-budget config escalates before provider call, and provider call count remains zero. |
| AC-008 | REQ-008 | Tests assert structured JSON/schema output instructions are present. |
| AC-009 | REQ-009 | Tests assert provider request payload evidence content is a `PromptExcerptSet`, not raw bundle facts. |

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Add `src/praetor/judgment/excerpt.py` for focused excerpt data structures and truncation policy. | Keeps excerpt hygiene testable without provider or engine setup. |
| DEC-002 | Add `src/praetor/judgment/prompt.py` for prompt payload construction. | Keeps provider request assembly separate from engine state transitions. |
| DEC-003 | Treat normalized fields, safe non-reserved top-level fields, `source_event_reference`, and `provenance_path` as prompt-eligible evidence fields; recursively exclude `raw_source`. | Minimal Task 14 implementation with stable fact IDs, walking-skeleton citation continuity, and no raw-source leakage. |
| DEC-004 | Use head+tail truncation for prompt-eligible string values because alert telemetry may contain unbounded adversarial text. | Satisfies the high-risk unbounded field requirement without adding field-specific future-policy logic. |
| DEC-005 | Keep config budget enforcement in `process_alert_intake` before building provider request. | Existing Outcome Matrix behavior already escalates `config_over_budget` without a provider call. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Write failing tests for excerpt construction, raw-source exclusion, incomplete warnings, structured-output instructions, and provider request payload shape. | `tests/judgment/test_prompt_isolation.py` | complete |
| TASK-002 | Implement excerpt dataclasses and 200-character head+tail truncation with exact omission markers. | `src/praetor/judgment/excerpt.py` | complete |
| TASK-003 | Implement prompt payload construction around `PromptExcerptSet`, verbatim config text, and structured-output instructions. | `src/praetor/judgment/prompt.py`, `src/praetor/judgment/__init__.py` | complete |
| TASK-004 | Wire `process_alert_intake` to build and pass the sanitized prompt payload to `JudgmentRequest`. | `src/praetor/engine/orchestrator.py` | complete |
| TASK-005 | Run scoped/full verification and update workflow + Memory Bank artifacts. | `.workflow/TASK-014/*`, `memory-bank/*` | complete |
