# Verifier Result — rfc-remediation-01-never-contain-logging

**Outcome:** PASS  
**Verifier:** skeptic-verifier (fresh context; implementer/reviewer claims treated as unevidenced)  
**Commit checked:** `1f541fb8fc7094fa2c102ee8198d350e997527ff` (= `HEAD`)  
**Scope:** task acceptance criteria only

## Claim under test

Malformed never-contain entries are logged on both defensive matcher skip branches in `praetor.config.live`, without changing matching or authorization outcomes.

## Independent commands (reproduced)

| Command | Result |
|---------|--------|
| `pytest tests/config/test_live_never_contain_matching.py -v` | **3 passed** in 0.15s (exit 0) |
| `ruff check .` | All checks passed! (exit 0) |
| `mypy .` | Success: no issues found in 134 source files (exit 0) |

Working tree for the two implementation paths matches the commit (`git diff 1f541fb --` empty for those files).

## Acceptance criteria

### AC1 — Both malformed-entry branches emit a warning through `praetor.config.live` — PASS

- `_logger = logging.getLogger(__name__)` at `src/praetor/config/live.py:15` → logger name `praetor.config.live`.
- `directive_matches_entry` logs on `PreflightError` then `return False` (`live.py:86-90`).
- `target_in_never_contain_list` logs on `PreflightError` then `continue` (`live.py:122-126`).
- Tests exercise both paths with `caplog.at_level(..., logger="praetor.config.live")` and assert the message substring; both PASSED under independent run.

Malformed fixture `{"target_type": "host"}` is non-vacuous: after key filtering, keys are `{"target_type"}`, which fails `canonical_target_specification`’s required key-set check (`live.py:23-30`).

### AC2 — Valid entries emit no warning; matching unchanged — PASS

- `test_target_in_never_contain_list_no_log_when_all_entries_valid` asserts `caplog.records == []` and `False` for a non-matching valid entry — PASSED.
- Parent vs `1f541fb` diff: success-path comparisons and return/`continue` control flow are identical; only `except PreflightError` arms gained `_logger.warning(...)`. No other functions in `live.py` changed in the commit.
- Warning calls exist only inside the two `except PreflightError` arms; valid canonicalization cannot reach them.

### AC3 — No disposition, authorization, or never-contain semantics change — PASS

- Commit touches only allowed files: `src/praetor/config/live.py` (+13/−2 logging) and `tests/config/test_live_never_contain_matching.py` (new).
- Skip outcomes preserved vs parent: still `return False` / `continue` on `PreflightError`; match predicates unchanged.
- No PolicyGate, disposition, stamp/ledger, or production validation-path edits in the commit.

## Attempts to refute (failed)

1. **Stale / mismatched tree** — `HEAD` is `1f541fb`; no dirty diff on the two paths.
2. **Tests not hitting new code** — all 3 collected and PASSED; malformed path requires the new warning for asserts to pass.
3. **Vacuous malformed fixture** — missing `target_id` fails key-set validation before any match comparison.
4. **Semantic drift via silent edits** — commit file list and function-level parent diff show additive logging only.
5. **Broad claim from narrow green** — packet-scoped commands all green; AC3 additionally grounded in diff inspection, not suite breadth.

## Residual notes (non-blocking; do not change outcome)

- Tests assert message substring only, not `record.levelno == logging.WARNING` (mirrors approved plan snippet).
- No dedicated valid-path no-log test for `directive_matches_entry`; covered by code inspection (warnings only in except arms).

## Verdict

**PASS** — all three acceptance criteria are backed by independently reproduced pytest/ruff/mypy evidence plus parent-vs-commit semantic inspection of the two skip branches.
