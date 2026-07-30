# Implementer Result — rfc-remediation-01-never-contain-logging

## Status

DONE_WITH_CONCERNS

## Model

composer-2.5

## Changed files

| File | Rationale |
|------|-----------|
| `src/praetor/config/live.py` | Added module `_logger` and warning calls on both `PreflightError` skip branches in `directive_matches_entry` and `target_in_never_contain_list`; return/skip behavior unchanged. |
| `tests/config/test_live_never_contain_matching.py` | New regression tests asserting warning visibility on malformed entries and no warnings on valid-only paths. |

## Red / green evidence

**Red** (`pytest tests/config/test_live_never_contain_matching.py -v` before implementation):

```
FAILED test_target_in_never_contain_list_skips_malformed_entry_and_logs
FAILED test_directive_matches_entry_returns_false_and_logs_on_malformed_entry
1 passed, 2 failed
```

Failures: `caplog.records` empty — no warning emitted yet; return values already correct.

**Green** (`pytest tests/config/test_live_never_contain_matching.py -v` after implementation):

```
3 passed in 0.14s
```

## Verification outputs

### pytest

```
tests/config/test_live_never_contain_matching.py::test_target_in_never_contain_list_skips_malformed_entry_and_logs PASSED
tests/config/test_live_never_contain_matching.py::test_target_in_never_contain_list_no_log_when_all_entries_valid PASSED
tests/config/test_live_never_contain_matching.py::test_directive_matches_entry_returns_false_and_logs_on_malformed_entry PASSED
3 passed in 0.14s
```

### ruff

```
All checks passed!
```

### mypy

```
Success: no issues found in 134 source files
```

## Commit

`1f541fb8fc7094fa2c102ee8198d350e997527ff`

Message: `config: log skipped malformed never-contain entries instead of silently dropping them`

## Concerns

- Source plan test snippet used non-existent `ContainmentTargetType`; tests use repo-correct `TargetType` instead.
- Source plan used quoted `"logging.LogCaptureFixture"` annotations; adjusted to `pytest.LogCaptureFixture` to satisfy ruff UP037 and match `tests/evals/test_real_provider_adversarial.py`.
