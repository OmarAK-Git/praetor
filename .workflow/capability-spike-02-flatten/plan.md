# capability-spike-02-flatten

## Goal

Add generic mechanical event flattener for Path B evidence facts (no hand-tuned per-event-type extraction).

## Scope

evals/capability/flatten.py + unit tests only.

## Tier

T2

## Allowed files

- evals/capability/flatten.py
- tests/evals/capability/test_flatten.py
- .workflow/capability-spike-02-flatten/

## Acceptance criteria

- flatten_event_to_fact emits EvidenceFact with flattened normalized_fields.
- resolve_provenance_path labels known sources; unknown uses SPIKE_UNKNOWN_SOURCE.
- Flattener stays mechanical (no per-EventID hand extraction).

## Verification commands

- `pytest tests/evals/capability/test_flatten.py -q`
- `ruff check evals/capability/flatten.py tests/evals/capability/test_flatten.py`
- `mypy evals/capability/flatten.py`

## Sources

- Plan Task 2: docs/superpowers/plans/2026-08-01-judgment-capability-spike.md
