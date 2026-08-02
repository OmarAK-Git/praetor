# capability-spike-06-cli

## Goal

Add offline-safe capability spike CLI and document it as non-gating in docs/eval_gates.md.

## Allowed files

- evals/capability_spike.py
- tests/evals/capability/test_cli.py
- docs/eval_gates.md
- .workflow/capability-spike-06-cli/

## Acceptance criteria

- main() exits 0 with skip message when PRAETOR_CAPABILITY_SPIKE unset.
- Enabled without API key still skips (no network).
- load_capture_events reads JSONL and skips blank/malformed lines.
- Harness source does not import the spike module.
- Non-gating section appended to docs/eval_gates.md.

## Verification

- `pytest tests/evals/capability/test_cli.py -q`
- `ruff check evals/capability_spike.py tests/evals/capability/test_cli.py`
- `mypy evals/capability_spike.py`
- `python -m evals.capability_spike`
