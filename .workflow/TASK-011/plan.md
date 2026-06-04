# Plan: TASK-011 — Revocation Feed Outbox, Exporter, Startup Recovery, Smoke Benchmark

## Goal

Deliver sequential revocation-feed JSONL export, startup recovery, feed-health signals for PolicyGate, and a smoke serialized-path benchmark per `docs/plan.md` Task 11 and `docs/spec.md` § RevocationFeed v1 / startup step 8.

**Authority:** `docs/plan.md` Task 11, `docs/spec.md` § RevocationFeed v1, `docs/contracts.md` §8, §12 (`revocation_feed_unhealthy`).

## Tier

T3 — Flight Recorder workflow.

## Scope

**In scope:**

- `src/praetor/revocation/{outbox,feed,exporter}.py`
- Additive SQLite schema for export retries, verified sequence, unhealthy flag
- `run_feed_startup_hook` wired from `open_state_store`
- `benchmarks/smoke_serialized_path.py`
- Tests: `tests/revocation/`, `tests/runtime/test_feed_startup_recovery.py`, `tests/benchmarks/test_smoke_benchmark.py`
- Scope guard: allow `revocation` package

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| `docs/` edits | Command hard limit |
| PolicyGate integration | Task 16 |
| Walking skeleton / intake | Task 12 |
| Ledger append on revocation paths | Task 12 (export only here) |
| Feed rotation | v1 explicitly absent |

## Design

1. **Feed record** — `build_feed_record()` maps `DirectiveRevocationRecord` + assigned `sequence_number`; checksum via `compute_feed_record_checksum`.
2. **Export** — single-threaded, strict sequence order from `last_verified_exported_sequence + 1`; JSONL append-only; post-write checksum verify.
3. **Retries** — per-row `export_retry_count`; exhaustion or verify failure → `feed_unhealthy` + durable `revocation_feed_unhealthy` health alert.
4. **PolicyGate probe** — `oldest_pending_feed_age_seconds()` uses `ledger_commit_at` of oldest `pending` outbox row.
5. **Startup** — export all pending before actuation; if still unhealthy or pending age > `max_revocation_feed_propagation_delay_seconds`, set degraded (blocks auto-contain via `is_feed_actuation_blocked()`).
6. **Smoke benchmark** — measure revocation write rate in `critical_transaction` against `provisional_alert_rate_targets` from active org config.

## Verification plan

- `pytest -q tests/revocation/ tests/runtime/test_feed_startup_recovery.py tests/benchmarks/`
- `pytest -q`
- `mypy src`
- `ruff check` on TASK-011 scope
- `python -m praetor.contracts.schema_export`

## Risks

| Risk | Mitigation |
|------|------------|
| Outbox schema migration on existing DBs | PRAGMA-driven `ALTER TABLE` additive columns |
| Health alert inside `critical_transaction` | Emit unhealthy alerts outside export tx (DEC-008 pattern) |
| CI flake on timing benchmark | Structural smoke test + optional rate assertion with generous floor |
