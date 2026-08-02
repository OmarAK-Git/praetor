# Verifier packet — capability-spike-06-cli

## Goal

Add offline-safe capability spike CLI and document it as non-gating in docs/eval_gates.md.

## Acceptance criteria

- main() exits 0 with skip message when PRAETOR_CAPABILITY_SPIKE unset.
- Enabled without API key still skips (no network).
- load_capture_events reads JSONL and skips blank/malformed lines.
- Harness source does not import the spike module.
- Non-gating section appended to docs/eval_gates.md.

## Changed files (commit 2450e66)

- evals/capability_spike.py
- tests/evals/capability/test_cli.py
- docs/eval_gates.md

## Commands

- `pytest tests/evals/capability/test_cli.py -q`
- `ruff check evals/capability_spike.py tests/evals/capability/test_cli.py`
- `mypy evals/capability_spike.py`
- `python -m evals.capability_spike`

## Manual

- Spike remains opt-in via env flag + key; not a CI gate.
- No src/praetor/ edits; no evals/harness.py or scenarios edits.

Implementer: `.workflow/capability-spike-06-cli/results/implementer-result.md`
Task scope. Write `results/verifier-result.md`.
