# capability-spike-03-bundle

## Goal

Add Path B bundle builder that reuses correlation window and host filters, then flattens all event types.

## Scope

evals/capability/bundle.py + unit tests only.

## Allowed files

- evals/capability/bundle.py
- tests/evals/capability/test_bundle.py
- .workflow/capability-spike-03-bundle/

## Acceptance criteria

- build_spike_bundle calls filter_events_in_window and filter_events_to_anchor_host from praetor.correlation.
- Non-1/4624 events appear in Path B bundles when in window/host.
- Window/host filtering matches production correlation helpers.

## Verification

- `pytest tests/evals/capability/test_bundle.py -q`
- `ruff check evals/capability/bundle.py tests/evals/capability/test_bundle.py`
- `mypy evals/capability/bundle.py`
