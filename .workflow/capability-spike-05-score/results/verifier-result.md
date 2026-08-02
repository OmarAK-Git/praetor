# Verifier result — capability-spike-05-score

## Verdict

**PASS** (claim survives)

## Claim under test

Commit `98debe4` adds scoring, A/B delta, and confound check for the capability spike: malicious correct on escalate/auto_contain; benign on standard_review; missing `proposed_disposition` excluded; `ab_delta` attributes A/B outcomes; `confound_check` flags separating features. PolicyGate not folded into score. No `src/praetor/**` edits.

## Fresh evidence (re-run this session)

| Command | Result |
|---------|--------|
| `pytest tests/evals/capability/test_score.py -q` | `10 passed in 0.32s` (exit 0) |
| `ruff check evals/capability/score.py tests/evals/capability/test_score.py` | All checks passed (exit 0) |
| `mypy evals/capability/score.py` | Success: no issues found (exit 0) |

Working tree for the two code files matches `98debe4` (`git diff 98debe4 --` empty).

## Acceptance criteria

| Criterion | Evidence | Status |
|-----------|----------|--------|
| Malicious correct on escalate/auto_contain | `_MALICIOUS_CORRECT`; `test_malicious_correct_on_escalate_or_auto_contain`; incorrect on `standard_review` | met |
| Benign correct on standard_review | `_BENIGN_CORRECT`; `test_benign_correct_only_on_standard_review` | met |
| Empty/missing proposed_disposition excluded | `score_path` filters `is not None`; `excluded_empty_bundle`; `test_missing_judgment_excluded_not_counted_wrong` | met |
| ab_delta A-wrong/B-right, both-wrong, dilution | `test_ab_delta_classifies_each_anchor`: m1 `(wrong,right)`, m3 `(wrong,wrong)`, m4 `(right,wrong)` | met |
| confound_check flags separating heuristics | `test_confound_check_flags_perfectly_separating_host`; shared-host negative | met |

## Manual checks

### PolicyGate not in score

- `score.py` scores only `obs.proposed_disposition`; no read of `final_disposition`, no PolicyGate import (PolicyGate mentioned only in module docstring).
- Fixture `_obs` always sets `final_disposition="escalate"`; `test_malicious_incorrect_on_standard_review` still expects `correct == 0` — would fail if gate output were scored.
- Live probe: proposed=`standard_review`, final=`escalate` → `score_path` returns `correct=0`.

### Commit `98debe4` has no `src/praetor`

`git show 98debe4 --name-status`:

- `A  evals/capability/score.py`
- `A  tests/evals/capability/test_score.py`

`findstr` on commit file list: no `src/praetor`. Diff pathspec `src/praetor/**` empty.

## Adversarial checks attempted

- **Stale evidence:** re-ran pytest/ruff/mypy this session; tree matches commit.
- **Gamed PolicyGate exclusion:** fixture plants conflicting `final_disposition`; incorrect-proposed tests still fail correctly.
- **Letter-not-intent:** implementation matches plan Task 5 verbatim (interfaces + scoring rule).
- **Broad claim / narrow check:** all four acceptance criteria have dedicated tests; dilution case covered via m4.

## Strongest reason for PASS

Fresh 10/10 green checks plus code that only reads `proposed_disposition`, with tests that would pass-fail invert if PolicyGate/`final_disposition` were scored; commit scope is exactly the two allowed files.
