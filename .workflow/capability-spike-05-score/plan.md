# capability-spike-05-score

## Goal

Add scoring, A/B delta attribution, and same-capture confound check for the capability spike.

## Allowed files

- evals/capability/score.py
- tests/evals/capability/test_score.py
- .workflow/capability-spike-05-score/

## Acceptance criteria

- Malicious correct on escalate/auto_contain; benign on standard_review.
- Empty/missing proposed_disposition excluded from score and counted separately.
- ab_delta attributes A-wrong/B-right vs both-wrong vs dilution cases.
- confound_check flags trivial heuristics that separate classes.

## Verification

- `pytest tests/evals/capability/test_score.py -q`
- `ruff check evals/capability/score.py tests/evals/capability/test_score.py`
- `mypy evals/capability/score.py`
