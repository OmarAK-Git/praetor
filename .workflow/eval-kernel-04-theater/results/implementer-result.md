# Implementer result — eval-kernel-04-theater

## Status

**Done** — Task 4 theater detector registry implemented per plan.

## Files changed

| File | Rationale |
|---|---|
| `evals/theater.py` | Named theater-detector registry with `TheaterContext`, `TheaterFinding`, six §8 detectors, and `run_theater_detector()`. |
| `tests/evals/test_theater.py` | TDD unit tests for unknown-name rejection and five trip conditions. |

## Interfaces delivered

- `TheaterContext` — frozen dataclass with scenario/arm/excerpt/scorecard/src/copy fields.
- `TheaterFinding` — frozen dataclass with `detector`, `tripped`, `message`.
- `DETECTORS` — registry mapping all six `THEATER_DETECTOR_NAMES` to callables.
- `run_theater_detector(name, ctx)` — dispatches by name; unknown names raise `KeyError("unknown theater detector: ...")`.

## Detectors (spec §8)

1. `label_leak` — trips on GT needles in `alert_identity` or `excerpt_blob`.
2. `stipulated_capability` — trips when `scorecard_is_quality_pass` is true.
3. `unearned_demo_claim` — scans `copy_roots` for unearned judgment claims.
4. `path_b_in_src` — AST scan of `src_root` for Path B module imports.
5. `post_hoc_protocol` — trips on protocol mutation markers in excerpt.
6. `gate_scored_as_judgment` — trips when quality pass uses PolicyGate layer.

## Verification

```
pytest tests/evals/test_theater.py -q
# 6 passed in 0.15s

ruff check evals/theater.py tests/evals/test_theater.py
# All checks passed!

mypy evals/theater.py
# Success: no issues found in 1 source file
```

## Commit

```
feat(evals): add named theater-detector registry
```

## Unresolved / out of scope

- Queue not marked done (per instructions).
- Production scenario wiring deferred to Task 5+.
- `post_hoc_protocol` has no dedicated trip test in plan Step 1 (covered by registry completeness via `THEATER_DETECTOR_NAMES` alignment).
