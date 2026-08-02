# Verifier result — capability-spike-04-runner (re-verify after 82b41ad)

## Verdict

**PASS** (claim survives)

## Claim under test

Fix commit `82b41ad` makes Path A pass `anchor_time` into `process_alert_intake` so in-window fixture events correlate, FakeProvider is consulted, and prior Task 4 acceptance still holds. No `src/praetor/**` or harness edits in that commit.

## Fresh evidence (re-run this session)

| Command | Result |
|---------|--------|
| `pytest tests/evals/capability/test_runner.py -q` | `5 passed in 1.16s` (exit 0) |
| `ruff check evals/capability/runner.py tests/evals/capability/test_runner.py` | All checks passed (exit 0) |
| `mypy evals/capability/runner.py` | Success: no issues found (exit 0) |

## Acceptance criteria

| Criterion | Evidence | Status |
|-----------|----------|--------|
| `run_anchor` produces Observations for PATH_A and PATH_B | `test_both_paths_produce_observations`; live probe → `path=correlation` and `path=flattened` | met |
| `proposed_disposition` from `result.edict.model_judgment` when present | `runner.py` `_observe` (L93–94): `edict.model_judgment.proposed_disposition.value` | met |
| `final_disposition` / `fault_flags` recorded | `_observe` L90, L96–104; live probe: `final=escalate`, `faults=('invalid_model_citation',)` | met |
| Offline FakeProvider tests pass | 5 passed; tests use `FakeProvider` only | met |
| **NEW:** Path A passes `anchor_time`; no `correlation_failure`; FakeProvider consulted | `intake_kwargs["anchor_time"] = anchor.anchor_time` at `runner.py:157`; `test_path_a_correlates_in_window_events` asserts flag absent and `proposed_disposition == STANDARD_REVIEW` (skeleton correlation-failure path proposes `escalate` with `judgment_provider_calls=0`, so STANDARD_REVIEW proves provider ran) | met |

## Commit scope (`82b41ad`)

`git show 82b41ad --name-only`:

- `.workflow/capability-spike-04-runner/results/implementer-result-fix.md`
- `evals/capability/runner.py`
- `tests/evals/capability/test_runner.py`

No `src/praetor/**`, no `evals/harness.py`. `HEAD` == `82b41ad`; working tree for the two code files matches the commit.

## Adversarial checks attempted

- **Stale evidence:** re-ran pytest/ruff/mypy against current tree at `82b41ad`.
- **Gamed assertion:** `"correlation_failure" not in fault_flags` matches `OutcomeMatrixFaultFlag.CORRELATION_FAILURE.value` (`"correlation_failure"`).
- **False provider consultation:** correlation-failure path sets skeleton proposed=`escalate` and never calls provider; test requires `standard_review` → cannot pass under the old bug.
- **Scope creep:** commit file list excludes harness/`src/praetor`.

## Strongest reason for PASS

Line `runner.py:157` plus regression test requiring FakeProvider's `STANDARD_REVIEW` (not skeleton `escalate`) independently prove the Path A `anchor_time` fix; fresh 5/5 green checks and commit scope hold.
