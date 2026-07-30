# Verifier Result — rfc-remediation-05-feed-size-warning

**Outcome:** PASS (survives)  
**Verifier:** skeptic-verifier (fresh context; implementer/reviewer claims treated as unevidenced)  
**Commit checked:** `03f62cbc25acc2bf5166d03ece83d40d22fb0246` (= `HEAD`)  
**Scope:** task acceptance criteria only (plan allowed paths)

## Claim under test

Emit an operator health warning when the append-only revocation feed exceeds a configured size threshold: above-threshold queues `revocation_feed_file_size_warning` via the existing health outbox; missing/below-threshold emits no warning; default database startup hook checks the configured default threshold; no rotation, truncation, segmentation, format, sequence, checksum, or actuation changes.

## Independent commands (reproduced)

| Command | Result |
|---------|--------|
| `pytest tests/revocation/test_feed_exporter.py -v` | **25 passed** in 4.07s (exit 0) |
| `ruff check .` | All checks passed! (exit 0) |
| `mypy .` | Success: no issues found in 134 source files (exit 0) |

Working tree for the three allow-listed paths is clean vs `HEAD`/`03f62cb` (`git diff HEAD --` empty for those files). Commit file set is exactly the allow-list: `constants.py`, `exporter.py`, `test_feed_exporter.py` (+127 lines only).

## Acceptance criteria

### AC1 — Above threshold queues `revocation_feed_file_size_warning` via health outbox — PASS

- `FEED_FILE_SIZE_WARNING_CODE = "revocation_feed_file_size_warning"` (`exporter.py:48`).
- `check_feed_file_size_warning` builds `SystemHealthAlert(alert_code=FEED_FILE_SIZE_WARNING_CODE, ...)` and calls `write_pending_health_alert` (`exporter.py:123-128`) — same outbox path as `_emit_feed_unhealthy_alert`.
- Independent probe: 1025-byte file with `warning_bytes=1024` → returns `True` and inserts outbox row with that alert code.
- `test_run_feed_startup_hook_emits_size_warning_when_threshold_exceeded` PASSED (helper above-threshold path).
- `test_run_feed_startup_hook_wires_size_warning_check` PASSED (`run_feed_startup_hook_for_db` with `feed_file_size_warning_bytes=1024`, whitespace feed so reconcile succeeds while `st_size > 1024`).

### AC2 — Missing / below threshold emits no warning — PASS

- Missing: `if not feed_path.exists(): return False` (`exporter.py:119-120`); independent probe with absent path → `False`, no size-warning outbox rows.
- Below: `st_size <= warning_bytes` → `False` (`exporter.py:121-122`); test PASSED for 100-byte file vs 1024; independent probe for equality (`st_size == warning_bytes`) also returns `False` (strict “above”).
- Hook path: `for_db` with small whitespace feed and `warning_bytes=1024` → no size-warning codes; `is_feed_actuation_blocked` / `is_feed_unhealthy` remain `False`.

### AC3 — Default database startup hook checks configured default threshold — PASS

- Constant: `DEFAULT_FEED_FILE_SIZE_WARNING_BYTES = 500_000_000` (`constants.py:15`).
- `run_feed_startup_hook_for_db` resolves `None` via lazy `from praetor.config.constants import DEFAULT_FEED_FILE_SIZE_WARNING_BYTES` then passes the int into `run_feed_startup_hook` (`exporter.py:524-534`).
- Independent mock: `run_feed_startup_hook_for_db(conn, db_path)` with no override calls `check_feed_file_size_warning(..., warning_bytes=500_000_000)`.
- Production caller unchanged in this commit: `open_state_store` imports `run_feed_startup_hook_for_db` and invokes it without `feed_file_size_warning_bytes` when an active snapshot exists (`state/store.py`), so the default path applies.

### AC4 — No rotation / truncation / segmentation / format / sequence / checksum / actuation changes — PASS

- Diff is additive only (constant, helper, optional kwargs, post-reconcile size check + `commit`, three tests).
- Size path never calls `set_feed_unhealthy`, never mutates the feed file, and documents observational-only intent (`exporter.py:114-117`).
- Existing no-rotation regression `test_feed_jsonl_has_no_rotation_machinery` still PASSED in the full exporter suite.

## Lazy-import / startup wiring (packet-required independent inspection)

- **Circular import:** Injecting a top-level `from praetor.config.constants import DEFAULT_FEED_FILE_SIZE_WARNING_BYTES` into a twin `exporter` module fails with `ImportError: cannot import name 'is_feed_actuation_blocked'` (cycle via `config` → … → `policy.gate` → `exporter`). Lazy import inside `for_db` is necessary and behaviorally equivalent for callers that omit the kwarg.
- **`run_feed_startup_hook` vs `for_db`:** Direct hook still treats `None` as skip (`exporter.py:506`); `for_db` always supplies an int after lazy resolve. Matches the source plan’s opt-in-vs-default split.
- **Reconcile-failure early return** skips the size check (`exporter.py:473-484` before the size block). Matches the approved source-plan control flow; not an AC failure for this task.

## Attempts to refute (failed)

1. **Stale / mismatched tree** — `HEAD` is `03f62cb`; allow-listed paths have empty diff vs commit.
2. **Misleading first test name games “hook” coverage** — first test only exercises the helper (as in the source plan), but the third test exercises `for_db` → hook → outbox; removing the hook size block would fail that wiring test.
3. **DEFAULT never proven by tests** — tests inject `1024`, but independent mock proves `for_db` without override passes `500_000_000`.
4. **Missing-file AC only in code, not tests** — behavior confirmed by direct probe; code short-circuits before outbox write.
5. **Scope creep / actuation side effects** — commit touches only three allowed files; below-threshold hook probe leaves actuation/unhealthy flags false.
6. **Checks pass without behavior** — above-threshold helper and wiring tests assert the specific alert code in `system_health_alert_outbox`; cannot pass via a pure no-op.

## Residual notes (non-blocking; do not change outcome)

- No dedicated unit test for missing-file helper or equality-at-threshold edge (both verified by probe/code).
- Size warning skipped on reconcile failure (plan-literal).
- Each above-threshold successful startup inserts a new outbox UUID (same pattern as unhealthy alerts).
- `open_state_store` only runs the feed hook when an active snapshot exists (pre-existing gate; outside this task’s file allow-list).

## Verdict

**PASS (survives)** — all four acceptance criteria are backed by independently reproduced pytest/ruff/mypy evidence, direct inspection of the size-check + `for_db` default wiring, a reproduced circular-import justification for the lazy import, and a mock proving the configured default threshold is what production `for_db` callers receive.
