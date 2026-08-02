# Implementer result — capability-spike-05-score

## Status

**Complete** — all verification commands green.

## Files changed

| File | Rationale |
|------|-----------|
| `evals/capability/score.py` | `PathScore` dataclass, `score_path`, `ab_delta`, and `confound_check` scoring `proposed_disposition` only (PolicyGate excluded) |
| `tests/evals/capability/test_score.py` | Ten offline tests covering malicious/benign correctness, exclusion of missing judgments, path filtering, unstable anchors, citation resolution rate, A/B delta, and confound check |

## Verification

```
pytest tests/evals/capability/test_score.py -q
# 10 passed in 0.35s

ruff check evals/capability/score.py tests/evals/capability/test_score.py
# All checks passed!

mypy evals/capability/score.py
# Success: no issues found in 1 source file
```

## Constraints honored

- No `src/praetor/` changes
- No `evals/harness.py` or `evals/scenarios/` changes
- PolicyGate not folded into score
- Queue not marked done

## Blockers

None.
