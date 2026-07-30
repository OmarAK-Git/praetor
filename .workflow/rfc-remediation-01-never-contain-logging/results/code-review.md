# Code Review — rfc-remediation-01-never-contain-logging

**Verdict: PASS**

**Commit reviewed:** `1f541fb8fc7094fa2c102ee8198d350e997527ff`  
**Scope:** RFC-003 observability — log malformed never-contain skips without changing match/auth outcomes  
**Plan:** `.workflow/rfc-remediation-01-never-contain-logging/plan.md`  
**Source:** `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md` Task 1

## Summary

The commit is a minimal, additive observability change on exactly the two defensive `PreflightError` branches named in the plan. Return/skip/continue behavior is unchanged. Only allowed files were touched. Expected repo adaptations (`TargetType`, `pytest.LogCaptureFixture`) are correct.

## Spec compliance

| Acceptance criterion | Result |
|---|---|
| Both malformed-entry branches emit a warning via `praetor.config.live` | Met — `_logger = logging.getLogger(__name__)` plus `_logger.warning(...)` in both `except PreflightError` arms |
| Valid entries emit no warning; matching unchanged | Met — happy-path return/`continue`/`True`/`False` logic identical to parent; test covers no-log valid path |
| No disposition, authorization, or never-contain semantics change | Met — signatures, match predicates, and skip-and-continue outcomes preserved |

**Preserved semantics (parent vs commit):**

- `directive_matches_entry`: still `return False` on `PreflightError`; success path still compares `directive.target_type.value` / `target_id` to canonical fields.
- `target_in_never_contain_list`: still `continue` on `PreflightError`; still returns `True` on first canonical match, else `False` after the loop.
- No other functions in `live.py` were modified (validation path, combined/reconciliation helpers untouched).

**Allowed files only:** `src/praetor/config/live.py` (modified), `tests/config/test_live_never_contain_matching.py` (added). Diff is +69/−2 with no unrelated product changes in the commit.

**Expected adaptations (not defects):**

- Plan snippet’s `ContainmentTargetType` does not exist; tests correctly use `TargetType` / `TargetType.HOST` from `praetor.contracts.containment`.
- Plan’s quoted `"logging.LogCaptureFixture"` replaced with `pytest.LogCaptureFixture` (ruff UP037 / repo convention). Behavior under test is unchanged.

## Correctness

- Malformed fixture `{"target_type": "host"}` correctly triggers `canonical_target_specification`’s key-set check (`PreflightError`), exercising the intended skip branches.
- Skip-and-continue is covered: malformed then valid still yields `True` for a matching target.
- `%s` / `exc` logging is safe and useful; `PreflightError` stringifies via its message.

No concurrency, error-handling, or return-value regressions found.

## Security

Observability-only. No new trust boundaries, deserialization, or permission changes. Logging the exception message on a defensive config path matches the approved RFC-003 rescope (log, do not halt).

## Simplicity

Matches the prescribed implementation almost verbatim. No speculative abstractions or drive-by edits.

## Tests

Three tests align with the plan:

1. Malformed + valid → match `True` + warning present.
2. Valid-only non-match → `False` + empty `caplog.records` (scoped to `praetor.config.live`).
3. Directive match on malformed → `False` + warning present.

Logger name scoping reduces false positives. Tests would fail without the warning calls (implementer red evidence: empty `caplog.records`).

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/config/test_live_never_contain_matching.py:30-32,56-58`** — Assertions check message substring only, not `record.levelno == logging.WARNING`. Acceptable; mirrors the approved plan snippet.

## Checked (audit trail)

- Diff of `1f541fb` vs parent for both files
- Parent `except PreflightError` bodies vs post-change (return/`continue` preserved)
- Plan acceptance criteria and Task 1 source steps
- `TargetType` existence vs absent `ContainmentTargetType`
- Commit file list vs allowed implementation files
- No PolicyGate / disposition / DEC-053 / validation-path edits in commit
