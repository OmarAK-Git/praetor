# Workflow Plan: TASK-026 — Mandatory Phase 2 Eval Harness

## Goal

Implement the mandatory Phase 2 eval harness with 14 schema-valid scenario fixtures, Outcome Matrix assertions (including `system_fault_escalation`), feed/account feature-gate invariants, and non-zero exit on safety failures.

## Tier

T3 — Flight Recorder workflow.

## Scope

### In scope

- `evals/harness.py` — scenario loader, runners, CLI entry (`main()` exits non-zero on failure)
- `evals/scenarios/*.yaml` — all 14 mandatory scenarios from `docs/plan.md` Task 26
- `evals/schemas/scenario_schema.json` — scenario fixture schema
- `tests/evals/test_eval_harness.py` — schema validation + full harness pass
- `.workflow/TASK-026/*` flight recorder artifacts
- Memory Bank updates

### Out of scope

- `docs/` edits (start-task hard limit)
- PolicyGate wiring into `engine/orchestrator.py` (follow-on)
- Task 27+ (real-provider adversarial probe, correlation gates)
- Metrics/annotation production wiring

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | All 14 mandatory scenarios exist as YAML fixtures and validate against `scenario_schema.json` |
| REQ-002 | Harness asserts disposition, fault flags, and `system_fault_escalation` per Outcome Matrix (§13) |
| REQ-003 | `revocation_feed_unhealthy` blocks auto_contain only; standard_review still flows in degraded mode |
| REQ-004 | `account_containment_disabled` and never-contain scenarios assert `system_fault_escalation=false` |
| REQ-005 | `prompt_construction_isolation` asserts raw-source exclusion and excerpt bounds |
| REQ-006 | Harness exits non-zero on any safety invariant failure |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–006 | `tests/evals/test_eval_harness.py` pass |
| AC-002 | Regression | Full `pytest -q`, `mypy src`, `ruff check src tests consumer_sdk` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Workflow artifacts | `.workflow/TASK-026/*` | completed |
| T-002 | Schema + scenario YAML + harness | `evals/*` | completed |
| T-003 | Tests + verification + Memory Bank | `tests/evals/*`, `memory-bank/*` | completed |

## Risks

- Walking skeleton engine does not wire PolicyGate; policy-gate scenarios run `evaluate_policy_gate` directly (matches existing test patterns).
- `account_auto_contain_enabled=true` rejected at preflight; account gate scenario uses default false config.
- Engine `auto_contain` proposals are downgraded in orchestrator; confirmed-malicious scenario uses policy_gate runner.

## Verification plan

- `python -m pytest -q tests/evals/test_eval_harness.py`
- `python -m evals.harness` (or `python evals/harness.py`)
- `python -m pytest -q`
- `python -m mypy src`
- `python -m ruff check src tests consumer_sdk`
