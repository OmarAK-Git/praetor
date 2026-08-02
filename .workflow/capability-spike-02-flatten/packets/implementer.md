# Implementer packet — capability-spike-02-flatten

## Objective

Add generic mechanical event flattener for Path B evidence facts (no hand-tuned per-event-type extraction).

## Relevant docs

- `docs/superpowers/plans/2026-08-01-judgment-capability-spike.md` — **Task 2** (follow tests/code verbatim)
- `docs/superpowers/specs/2026-08-01-capability-spike-design.md` (flattener must stay dumb/mechanical)

## Allowed files

- evals/capability/flatten.py
- tests/evals/capability/test_flatten.py
- .workflow/capability-spike-02-flatten/

## Do not touch

- src/praetor/**
- evals/harness.py / evals/scenarios/**
- praetor.judgment.agentic
- Do not reimplement correlation window/host filters here

## Acceptance criteria

- flatten_event_to_fact emits EvidenceFact with flattened normalized_fields.
- resolve_provenance_path labels known sources; unknown uses SPIKE_UNKNOWN_SOURCE.
- Flattener stays mechanical (no per-EventID hand extraction).

## Instructions

1. Implement Task 2 from the plan exactly (TDD).
2. Run verification commands until green.
3. Do not mark queue done; do not run phase exit.
4. Commit with: `Add generic event flattener for capability spike Path B.`

## Verification commands

- `pytest tests/evals/capability/test_flatten.py -q`
- `ruff check evals/capability/flatten.py tests/evals/capability/test_flatten.py`
- `mypy evals/capability/flatten.py`

Write `.workflow/capability-spike-02-flatten/results/implementer-result.md` when done.
