# Progress Log

## 2026-06-04 — TASK-011 complete

- Revocation feed package: outbox export metadata, JSONL exporter, startup recovery hook, PolicyGate age probe, unhealthy transition + health alert.
- Benchmark: `benchmarks/smoke_serialized_path.py` vs `provisional_alert_rate_targets`.
- Verification: revocation+runtime+benchmark **11**, suite **302**, `mypy src` OK (59 files).
- Flight Recorder: `.workflow/TASK-011/`.

## 2026-06-04 — TASK-010 complete

- TASK-010 (revised): contracts §7a pin, startup hook in `open_state_store`, 29 ledger tests, schema drift check, audit/deletion/error-normalization coverage.

## 2026-06-03 — TASK-009 complete

- Org config package, example YAML, contracts §3a pins, cross-cutting store/hashing/contracts wiring.
- Verification: config **55**, suite **254**, `mypy src` OK, VERIFY-004/004b ruff OK.
- Flight Recorder: `.workflow/TASK-009/` closed.

## 2026-06-03 — TASK-009 third reopen (verification green, not closed)

- Local gaps: strict policy integers, `PreflightError` on binding serialize failures, fetch verifies JSON `snapshot_hash`, multi-verbatim per binding hash, stable health pending ids + activation/emergency drain.
- Tests: `tests/config/` — **55**; full `pytest -q` → **254**; `mypy src` OK; scoped TASK-009 `ruff` OK.
- `docs/contracts.md` §3a updated (hash vector, verbatim render rows, fetch integrity).
- Deferred: ledger chain (Task 10), intake `config_over_budget` gate (Task 12), repo-wide ruff E501.

## 2026-06-03 — TASK-009 reopen (gate review) — superseded

- Earlier pass claimed 29/228; superseded by third reopen evidence above.

## 2026-06-03 — TASK-009 complete (superseded by reopen)

- **`src/praetor/config/`:** loader, preflight, snapshot hash, activation with post-activation reconciliation, emergency never-contain, SQLite state for active config / emergencies / outstanding directives.
- **`configs/example_org.yaml`:** valid reference config.
- **`StateStore.write_automated_revocation_in_transaction`:** avoids nested `critical_transaction` during activation/emergency scans.
- Tests: `tests/config/` — **22** tests.
- Verification: `pytest -q` → 218 passed; `mypy src` → 47 files pass.
- Flight Recorder: `.workflow/TASK-009/`.
- Gap: ledger hash-chain append (Task 10); provisional hard character budget constant; intake `config_over_budget` gate (Task 12).

## 2026-06-01 — TASK-008 verification hardening (reopen)

- **G-1 fixed:** `FailingJsonlSink` moved to `tests/alerts/_fakes.py`; removed from production API.
- **G-2 fixed:** `SystemHealthAlert` docstring corrected — contract is payload; delivery in SQLite (DEC-026).
- **G-3 fixed:** `_deliver_to_sink` catches all `Exception`; records `exception_type`.
- **G-4–G-13 fixed:** 14 new tests — record guards, FK regression, nested critical tx, duplicate alert_id, fail→fail, at-least-once JSONL, retry query, import smoke, non-OSError sink.
- **G-14 documented:** `_initialized_conn_ids` v1 single-connection lifetime comment.
- Tests: `tests/alerts/test_system_health_outbox.py` — **23** tests.
- Verification: `pytest -q` → 196 passed; `mypy src` → 37 files pass; `ruff check` pass.

## 2026-06-01 — TASK-008 complete

- **`src/praetor/alerts/`:** `outbox.py`, `system_health.py` — durable SQLite health alert outbox; per-channel delivery tracking (`jsonl`, `stdout`); persist-before-deliver; retry failed channels; future channels via delivery table rows.
- Tests: `tests/alerts/test_system_health_outbox.py` — **9** tests.
- Verification: `pytest -q` → 182 passed; `mypy src` → 37 files pass.
- Flight Recorder: `.workflow/TASK-008/`.
- Gap: startup delivery worker (Task 11–12); emitter wiring (Task 9+).

## 2026-06-01 — TASK-007 verification hardening (reopen)

- **G-1 fixed:** `ConnectionError`/transport ambiguity → durable `unknown` via `_is_backend_ambiguity`; programmer `ValueError` not swallowed.
- **G-2–G-9 fixed:** 10 new tests — pending restart recovery, EMPTY_BUNDLE path, cached failed terminal, payload authority, DEC-022 additive schema, idempotent recovery path, `record_stamp_outcome` PENDING guard, `processing_attempt_identity` semantics (DEC-023).
- **G-10 deferred:** outbox timestamps use `isoformat()` (+00:00); Task 23 hazard if copied into hashed edict fields.
- **G-11 documented:** per-conn schema cache validates table exists (recycled `id(conn)` safety).
- Tests: `tests/tickets/test_stamp_outbox.py` — **21** tests.
- Verification: `pytest -q` → 173 passed; `mypy src` → 34 files pass.

## 2026-06-01 — TASK-007 complete

- **`src/praetor/tickets/`:** `outbox.py`, `stamp.py` — durable SQLite stamp outbox keyed by `stamp_id`; pending before external call; `succeeded`/`failed`/`unknown` outcomes; recovery retry with same `stamp_id`.
- Tests: `tests/tickets/test_stamp_outbox.py` — 11 tests.
- Verification: `pytest -q` → 163 passed; `mypy src` → 34 files pass.
- Flight Recorder: `.workflow/TASK-007/`.
- Gap: attempt FSM / edict append wiring (Task 23); startup recovery enumeration (Task 11–12).

## 2026-06-01 — TASK-006 verification fix pass

- Added 20 tests: feed sequence reopen/rollback, manual revocation rollback, completed-edict conflict, FSM negatives, idempotency duplicate, schema version reject, abort same-input retry, singleton contract.
- Implementation: `IncompatibleSchemaError`, `IdempotencyKeyConflictError`, `verify_schema_version`, `read_feed_sequence_next`.
- Verification: `pytest -q` → 152 passed; Task 6 file → **32** tests collected; `mypy src` pass.
- Artifacts corrected (V-002 wording, test count).

## 2026-06-01 — TASK-006 complete

- **`src/praetor/state/`:** `store.py`, `attempts.py`, `completed_decisions.py`, `idempotency.py` — attempt FSM, three-tuple dedup, manual/automated revocation + feed outbox sequence.
- Tests: `tests/state/test_attempt_lifecycle.py` — 32 tests (after fix pass).
- Verification: `pytest -q` → 152 passed; `mypy src` → 31 files pass.
- Flight Recorder: `.workflow/TASK-006/`.
- Gap: ledger chain append (Task 10); feed export (Task 11); enumeration helpers (11/12).

## 2026-06-01 — TASK-005 reopen complete

- **DEC-017:** `init_state_dir` one-shot WAL bootstrap; guard verify-only.
- **DEC-018:** nested `critical_transaction` forbidden (per-connection sentinel).
- **DEC-019:** Windows `msvcrt.locking` ratified vs spec `CreateFile` wording.
- **`verify_synchronous`:** `REQUIRED_SYNCHRONOUS_MIN=1` (NORMAL).
- Tests: 28 startup guard + bare-BEGIN scope guard; 119 total `pytest`.
- Verification: `mypy src` → 27 files pass.
- Gap: process-exit wrapper deferred to Task 12.

## 2026-06-01 — TASK-005 complete

- **`src/praetor/runtime/singleton.py`:** OS-level singleton file lock (`flock` on POSIX, `msvcrt.locking` on Windows); held for process lifetime; non-zero exit code on contention.
- **`src/praetor/state/sqlite_guard.py`:** WAL journal mode verification, explicit `isolation_level=None`, `critical_transaction` with `BEGIN IMMEDIATE`, `run_startup_sqlite_guard` entry point.
- Tests: `tests/runtime/test_startup_guard.py` — 13 tests including subprocess second-process block.
- Verification: `pytest -q` → 107 passed; `mypy src/praetor/runtime src/praetor/state`; `ruff check` on new modules.
- Flight Recorder: `.workflow/TASK-005/`.
- Gap: full SQLite PRAGMA list deferred to absent `docs/operator_runbook.md` (Task 35).

## 2026-06-01 — TASK-004 complete

- **`src/praetor/auth/`:** `Principal`, role literals, `TokenVerifier`, three external surfaces, `verified_record_identity` (rejects self-asserted overrides), `guard_internal_only` + `authenticate_external_write` for internal-op enforcement.
- Tests: `tests/auth/test_auth_primitives.py` — 28 tests.
- Tooling: mypy/ruff added to dev deps; auth module passes strict mypy and ruff.
- Verification: `pytest -q` → 90 passed; `mypy src/praetor/auth`; `ruff check src/praetor/auth tests/auth`.
- Flight Recorder: `.workflow/TASK-004/`.

## 2026-06-01 — TASK-003 complete (doc-first correction)

- **`docs/contracts.md`:** added §5 `stamp_id` (four-part delimited hash over completed-edict three-tuple; stable across attempts for outbox recovery idempotency); ratified §7 `EMPTY_BUNDLE` preimage `praetor:v1:empty_bundle`; renumbered §6–§15.
- **`src/praetor/hashing/`:** canonical serialization; `derive_decision_id`, `derive_idempotency_key`, `derive_stamp_id` (three-tuple only), feed checksum, never-contain hash.
- Tests: `tests/hashing/test_canonical.py` — includes stamp stability across attempts; scope guard allows `docs/contracts.md` only.
- Verification: `pytest -q` → 62 passed.
- Flight Recorder: `.workflow/TASK-003/`.

## 2026-06-01 — TASK-002 complete

- Implemented 14 versioned Pydantic v2 contracts under `src/praetor/contracts/` with `extra=forbid`, Literal `schema_version` / `record_type`, and §10–§11 validators.
- Generated deterministic JSON Schema artifacts in `schemas/` (not authoritative).
- Tests: `tests/contracts/` — round-trip, negative validation, export stability, scope guard.
- Verification: `pytest -q` → 36 passed; `python -m praetor.contracts.schema_export`.
- Flight Recorder: `.workflow/task-002/`.

## 2026-05-31 — TASK-001 complete

- Implemented repo skeleton: `pyproject.toml` (hatchling, `requires-python >=3.11`), `src/praetor/`, smoke tests, fixture manifest stub.
- Verification: `pip install -e ".[dev]"`, `pytest -q` → 2 passed.
- Flight Recorder: `.workflow/task-001/` (plan, verification, review, final-report).

## 2026-05-31 — Memory Bank initialized

- Read authoritative planning docs: `docs/prd.md`, `docs/spec.md`, `docs/plan.md`, `docs/contracts.md`.
- Populated Memory Bank to summarize and index docs for agent operations.

## Project state

| Area | State |
|------|--------|
| Product definition | Complete in `docs/` |
| Implementation plan | Complete — 35 tasks in `docs/plan.md` |
| Package / tests | Task 1 done — `pytest` runs, `praetor` imports |
| Contracts | Task 2 done — `src/praetor/contracts/`, `schemas/` |
| Hashing | Task 3 done — `src/praetor/hashing/` + `docs/contracts.md` §1–§9 |
| Auth | Task 4 done — `src/praetor/auth/` |
| Runtime / startup guard | Task 5 done — `src/praetor/runtime/`, `src/praetor/state/sqlite_guard.py` |
| State store / lifecycle | Task 6 done — `src/praetor/state/{store,attempts,completed_decisions,idempotency}.py` |
| Ticket stamp outbox | Task 7 done — `src/praetor/tickets/{outbox,stamp}.py` |
| SystemHealthAlert outbox | Task 8 done — `src/praetor/alerts/{outbox,system_health}.py` |
| Org config | Task 9 done — `src/praetor/config/` |
| Ledger hash chain | Task 10 done — `src/praetor/ledger/` |
| Revocation feed export | Task 11 done — `src/praetor/revocation/` |
| CI / eval harness | Not started (Task 26+) |
| Operator runbooks | Not in repo yet (Task 35) |

## Next recommended steps

1. TASK-012 — walking skeleton decision flow and recovery per `docs/plan.md`.
