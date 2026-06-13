# Workflow Plan: TASK-025 — Analyst Annotation Storage

## Goal

Implement durable analyst annotation storage (`annotations/store.py`) enforcing schema cross-field validation, verified reviewer identity, linkage to existing `decision_id`, and immutability of prior edict ledger hashes.

## Tier

T3 — Flight Recorder workflow.

## Scope

### In scope

- `src/praetor/annotations/store.py` — SQLite schema, submit/fetch, decision existence check
- `tests/annotations/test_annotations.py` — all plan test-first criteria
- `tests/contracts/test_scope_guard.py` — allow `annotations` package
- `.workflow/TASK-025/*` flight recorder artifacts
- Memory Bank updates

### Out of scope

- `docs/` edits (start-task hard limit)
- Analyst UI / HTTP API
- Ledger hash-chain append for annotations (separate table; edicts unchanged)
- Future tasks (26+)

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | `AnalystAnnotation` cross-field validation enforced in both directions at store time |
| REQ-002 | `reviewer_identity` comes from verified principal via `verified_record_identity` |
| REQ-003 | Annotation links to an existing `decision_id` (completed_decisions or ledger edict) |
| REQ-004 | Storing an annotation does not alter a prior edict's `ledger_current_hash` |
| REQ-005 | Analyst role required (`authenticate_annotation_submission`) |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–005 | `tests/annotations/test_annotations.py` pass |
| AC-002 | Regression | Full `pytest -q`, `mypy src`, `ruff check src tests consumer_sdk` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Workflow artifacts | `.workflow/TASK-025/*` | completed |
| T-002 | Tests + annotations store | `annotations/*`, `tests/annotations/*`, scope guard | completed |
| T-003 | Verification + Memory Bank | `.workflow/TASK-025/*`, `memory-bank/*` | completed |

## Risks

- Decision existence may be ledger-only (walking-skeleton tests) or completed_decisions — check both.
- `AnalystAnnotation` has no `decision_id` field; linkage is store metadata, not contract field.

## Verification plan

- `python -m pytest -q tests/annotations/test_annotations.py`
- `python -m pytest -q`
- `python -m mypy src`
- `python -m ruff check src tests consumer_sdk`
