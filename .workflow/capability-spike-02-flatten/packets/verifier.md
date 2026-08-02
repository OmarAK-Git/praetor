# Verifier packet — capability-spike-02-flatten

## Goal

Add generic mechanical event flattener for Path B evidence facts (no hand-tuned per-event-type extraction).

## Acceptance criteria

- flatten_event_to_fact emits EvidenceFact with flattened normalized_fields.
- resolve_provenance_path labels known sources; unknown uses SPIKE_UNKNOWN_SOURCE.
- Flattener stays mechanical (no per-EventID hand extraction).

## Changed files (commit 41eae19)

- evals/capability/flatten.py
- tests/evals/capability/test_flatten.py

## Verification commands

- `pytest tests/evals/capability/test_flatten.py -q`
- `ruff check evals/capability/flatten.py tests/evals/capability/test_flatten.py`
- `mypy evals/capability/flatten.py`

## Manual checks

- Confirm flattener does not reimplement correlation window/host filters.
- No src/praetor/ edits.

## Implementer result

`.workflow/capability-spike-02-flatten/results/implementer-result.md`

Treat implementer claims as unevidenced. Task scope only. Write `results/verifier-result.md`.
