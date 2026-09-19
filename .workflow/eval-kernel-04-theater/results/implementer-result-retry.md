# Implementer result (retry) — eval-kernel-04-theater

## Status

**Done** — blocking code-review finding addressed.

## Files changed

| File | Rationale |
|---|---|
| `tests/evals/test_theater.py` | Added clean-path parametrized tests for all six detectors, `post_hoc_protocol` trip test, and `DETECTORS` ↔ `THEATER_DETECTOR_NAMES` pin. |

## Coverage added

| Detector | Trip test | Clean test |
|---|---|---|
| `label_leak` | `test_label_leak_trips_on_expected_class_in_excerpt` | parametrized |
| `stipulated_capability` | `test_stipulated_capability_trips_on_quality_pass` | parametrized |
| `unearned_demo_claim` | `test_unearned_demo_claim_trips_when_primary_unearned` | parametrized |
| `path_b_in_src` | `test_path_b_in_src_trips_on_flatten_import` | parametrized |
| `post_hoc_protocol` | `test_post_hoc_protocol_trips_on_relabel_marker` | parametrized |
| `gate_scored_as_judgment` | `test_gate_scored_as_judgment_trips_on_quality_from_policy_gate` | parametrized |

Unknown-name coverage retained: `test_unknown_detector_raises`.

Registry completeness pin: `test_detectors_match_theater_names`.

## Verification

```
pytest tests/evals/test_theater.py -q
# 14 passed in 0.29s

ruff check evals/theater.py tests/evals/test_theater.py
# All checks passed!

mypy evals/theater.py
# Success: no issues found in 1 source file
```

## Commit

```
test(evals): add trip+clean coverage for all theater detectors
```

## Unresolved

- Queue not marked done (per instructions).
- `evals/theater.py` unchanged; implementation already matched plan.
