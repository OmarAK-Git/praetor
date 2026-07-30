# Code Review — rfc-remediation-05-feed-size-warning

**Verdict: PASS**

**Commit reviewed:** `03f62cbc25acc2bf5166d03ece83d40d22fb0246`  
**Scope:** RFC-002 (rescoped) / DEBT-042 — operator size-warning health alert for the unrotated revocation feed  
**Plan:** `.workflow/rfc-remediation-05-feed-size-warning/plan.md`  
**Source:** `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md` Task 5  
**Implementer result:** `.workflow/rfc-remediation-05-feed-size-warning/results/implementer-result.md`

## Summary

Additive observational check: when the feed file exists and `st_size > warning_bytes`, enqueue `revocation_feed_file_size_warning` via the existing `SystemHealthAlert` + `write_pending_health_alert` outbox. No feed mutation, no actuation-gate changes, no format/sequence/checksum changes. Commit touches only the three allowed files; message matches the source plan.

## Spec compliance

| Acceptance criterion | Result |
|---|---|
| Above-threshold feed queues `revocation_feed_file_size_warning` through existing health-alert outbox | Met — `check_feed_file_size_warning` builds `SystemHealthAlert(alert_code=FEED_FILE_SIZE_WARNING_CODE)` and calls `write_pending_health_alert` |
| Missing or below-threshold feed emits no warning | Met — `exists()` short-circuit; `st_size <= warning_bytes` returns `False` without write |
| Default database startup hook checks the configured threshold | Met — `run_feed_startup_hook_for_db` resolves `None` → `DEFAULT_FEED_FILE_SIZE_WARNING_BYTES` (500_000_000) then passes it into the hook |
| No rotation, truncation, segmentation, feed-format, sequence, checksum, or actuation-state changes | Met — see boundary audit below |

**Interfaces (source plan):** `check_feed_file_size_warning(conn, feed_path, *, warning_bytes: int) -> bool` present; alert code and outbox path match `_emit_feed_unhealthy_alert`.

**Allowed files only:** `constants.py`, `exporter.py`, `test_feed_exporter.py`.

**Expected adaptations (not defects):**

- Plan’s top-level `from praetor.config.constants import DEFAULT_FEED_FILE_SIZE_WARNING_BYTES` and `for_db(..., feed_file_size_warning_bytes: int = DEFAULT_...)` would circular-import: loading `praetor.config` runs package `__init__` → … → `policy.gate` → `revocation.exporter` while exporter is still partial (`ImportError: cannot import name 'is_feed_actuation_blocked'` — reproduced by loading twin source as that module name). Lazy import inside `run_feed_startup_hook_for_db` when the arg is `None` is the correct AG-0021-style fix; runtime default behavior matches the plan.
- Packet required a startup-hook wiring test beyond the plan’s two helper tests; third test added appropriately.

## Boundary audit (no-rotation / no-actuation)

Diff does **not** modify:

- `FileFeedJsonlSink.append_line` / sink behavior
- `validate_feed_file_prefix`, sequence assignment, checksum verification
- `is_feed_actuation_blocked` body or call semantics
- `set_feed_unhealthy` / unhealthy transition logic (size path never calls them)
- JSONL format, disposition, authorization, DEC-053 ordering

`check_feed_file_size_warning` only `exists`/`stat`s and writes a health-alert outbox row. Docstring correctly states observational-only intent.

## Circular-import workaround

Justified and necessary (see reproduction above). Signature `feed_file_size_warning_bytes: int | None = None` on `for_db` plus lazy resolve is behaviorally equivalent to the plan’s defaulted `int` for all current callers (including `open_state_store`, which omits the kwarg). `run_feed_startup_hook` still treats `None` as “skip check,” preserving opt-in for direct callers — as in the plan.

## Default threshold behavior

- Constant `DEFAULT_FEED_FILE_SIZE_WARNING_BYTES = 500_000_000` with operator-visibility / non-rotation comments matches the plan verbatim.
- Strict inequality `st_size <= warning_bytes` → warn only when size **crosses** the threshold (equality does not warn) — consistent with “above-threshold” / “crosses.”
- Production path: `open_state_store` → `run_feed_startup_hook_for_db(...)` without override → default applied.

## Transaction / commit behavior

- `write_pending_health_alert` already persists inside `critical_transaction` (BEGIN IMMEDIATE + COMMIT).
- Trailing `conn.commit()` after the size check matches the plan and mirrors `_transition_feed_unhealthy`; redundant for the alert row but harmless (no partial write group introduced; single-alert write is already atomic per AG-0018-style outbox persist).

## Duplicate alert semantics

- No stable `alert_id` → each above-threshold invocation inserts a **new** outbox row (new UUID), same pattern as `_emit_feed_unhealthy_alert`.
- Plan wording “(re)confirmed necessary” and the shared unhealthy-alert path make re-emit on each successful startup intentional, not a silent dedupe bug.
- Outbox idempotency only applies to duplicate `alert_id` with identical payload — not relevant here.

## Startup normal vs reconcile-failure paths

- **Normal path:** After successful reconcile + export (+ optional unhealthy transition), if threshold is set, size check runs then commit. Wiring test uses `b"\n" * 2048`: `validate_feed_file_prefix` treats whitespace-stripped content as empty with `last_verified=0` (reconcile succeeds) while `st_size` still exceeds the test threshold — correctly exercises the post-reconcile branch without fabricating valid JSONL.
- **Reconcile-failure early return:** Size check is **skipped** when `reconcile_feed_metadata_against_jsonl` returns `False`. This matches the source-plan control flow exactly (check is after the early return). Not a spec deviation; operators still get feed-unhealthy signaling on integrity failure. Noted as a minor observability gap only.

## Filesystem races / errors

- Plan-prescribed `exists()` then `stat()` has a narrow TOCTOU/`OSError` window (delete/permission between checks) that could surface as an uncaught exception on an observational path.
- v1 single-writer + plan-literal code → track only; not blocking against approved requirements.

## Correctness

- Missing file → `False`, no alert.
- Below/equal threshold → `False`, no alert.
- Above threshold → alert queued, `True`.
- Helper does not touch actuation state or the feed file.
- Lazy default ensures `for_db` always supplies an int to the hook’s `is not None` gate.

## Security

Observability-only. No new trust boundaries, no permission widening, no feed rewrite, no secrets. Alert payload is alert_code + timestamp only.

## Simplicity / scope

Minimal and plan-shaped. No new tables, fault flags, dependencies, or rotation machinery. Diff +127 lines across the three allowed files.

## Tests

Fresh re-run: `pytest tests/revocation/test_feed_exporter.py -k "size_warning or wires_size" -v` → **3 passed**.

| Test | What it proves |
|---|---|
| `test_run_feed_startup_hook_emits_size_warning_when_threshold_exceeded` | Helper emits outbox row when size > threshold (plan name; tests helper directly) |
| `test_check_feed_file_size_warning_no_alert_below_threshold` | No alert when below threshold |
| `test_run_feed_startup_hook_wires_size_warning_check` | `run_feed_startup_hook_for_db` wires check through startup (packet requirement) |

Would fail without the helper / without wiring. Cannot pass via a pure no-op on the above-threshold or wiring cases.

Gaps (non-blocking): no explicit missing-file helper test; default 500 MB value not asserted (tests inject 1024 — appropriate); no reconcile-failure × large-file case (plan skips that path).

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`exporter.py:473-484` / startup reconcile-failure:** Size warning intentionally omitted on reconcile failure (plan control flow). Large-but-corrupt feeds rely on unhealthy alerts only — acceptable for this task; track if operators later want size visibility even when reconcile fails.

2. **`exporter.py:119-121`:** `exists()`/`stat()` TOCTOU and uncaught `OSError` on a purely observational check could abort startup in rare FS error cases. Plan-literal; consider catch-and-skip later if production sees it.

3. **Duplicate outbox rows:** Every successful above-threshold startup inserts a new `revocation_feed_file_size_warning` row (new UUID). Matches unhealthy-alert pattern and “(re)confirmed” wording; operators may want rate-limit/dedupe later — out of scope here.

4. **`test_run_feed_startup_hook_emits_size_warning_when_threshold_exceeded`:** Name implies hook coverage; body only exercises the helper (as in the source plan). Real hook coverage is the third test — rename later if confusing.

## Verdict rationale

Implements Task 5 / run-plan acceptance with required wiring test; justified lazy-import adaptation preserves default threshold behavior without circular import; absolute no-rotation / no-actuation boundaries hold; no Critical or Important defects. **PASS** — ready for skeptic-verify.
