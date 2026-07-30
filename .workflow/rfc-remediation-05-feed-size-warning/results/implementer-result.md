# Implementer Result — rfc-remediation-05-feed-size-warning

## Status

**done**

## Commit

`03f62cb` — `revocation: add operator size-warning health alert for the unrotated feed file`

## Changes

| File | Rationale |
|------|-----------|
| `src/praetor/config/constants.py` | Added `DEFAULT_FEED_FILE_SIZE_WARNING_BYTES` (500 MB provisional operator threshold). |
| `src/praetor/revocation/exporter.py` | Added `check_feed_file_size_warning`, wired into `run_feed_startup_hook` / `run_feed_startup_hook_for_db` via existing `SystemHealthAlert` + `write_pending_health_alert` path. |
| `tests/revocation/test_feed_exporter.py` | TDD: above-threshold, below-threshold, and startup-hook wiring tests. |

## Verification

| Command | Result |
|---------|--------|
| `pytest tests/revocation/test_feed_exporter.py -k size_warning -v` | 3 passed (red first: `ImportError: cannot import name 'check_feed_file_size_warning'`) |
| `pytest tests/revocation/test_feed_exporter.py -v` | 25 passed |
| `ruff check` (allowed files) | All checks passed |
| `mypy .` | Success: no issues found in 134 source files |

## Concerns

- **Circular import:** Top-level `from praetor.config.constants import DEFAULT_FEED_FILE_SIZE_WARNING_BYTES` in `exporter.py` triggers a cycle (`config.__init__` → … → `policy.gate` → `revocation.exporter`). Resolved with lazy import inside `run_feed_startup_hook_for_db` when `feed_file_size_warning_bytes` is `None`.
- **Early-return path:** Size warning runs only after the main startup-hook path completes; reconcile-failure early returns skip the check. The wiring test uses a whitespace-only feed file (reconcile treats as empty, `st_size` still exceeds threshold).
