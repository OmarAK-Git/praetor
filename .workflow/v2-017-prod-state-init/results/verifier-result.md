# Verifier Result — V2-017 Production State Initialization Guard

verification_model: claude-opus-4-8-thinking-high
outcome: pass

## Scope

Verified ONLY the four V2-017 acceptance criteria. Phase/sprint-level items
(V2-018..V2-023, V2 Gate 3) were explicitly excluded and not assessed.

## Method

Treated implementer claims as unevidenced. Read the actual source
(`src/praetor/policy/state.py`, `src/praetor/state/store.py`,
`src/praetor/runtime/startup.py`, `tests/runtime/test_production_state_init.py`,
and `src/praetor/judgment/provider_health_breaker.py`) and re-ran the
verification command myself.

## Per-Criterion Evidence

### Criterion 1 — open_production_state_store creates or asserts all required policy tables (PASS)

- `open_production_state_store` (`src/praetor/runtime/startup.py:12-25`) opens via
  `open_state_store(..., singleton=...)` then calls
  `assert_production_policy_tables(store.conn)`.
- `open_state_store` runs the singleton path and, only when a singleton is held,
  calls `ensure_production_policy_tables(conn)` (`src/praetor/state/store.py:367-370`),
  which runs `init_policy_state_schema` (rate counters + breakers) and
  `init_provider_health_breaker_schema` (provider_health_metrics + additive cols).
- `assert_production_policy_tables` (`src/praetor/policy/state.py:90-96`) fails
  closed via `StartupGuardError` if any of the 5 required tables is missing, so the
  entrypoint genuinely gates on the wiring (not a no-op).
- Test `test_production_state_store_creates_required_policy_tables` asserts all 5
  tables present, breaker cols `half_open`/`opened_at` exist, and
  `provider_health_metrics` row id=1 seeded. PASSED.

### Criterion 2 — Older additive fixtures get new tables via CREATE TABLE IF NOT EXISTS (PASS)

- `_POLICY_STATE_DDL` uses `CREATE TABLE IF NOT EXISTS` (`state.py:19-41`);
  `init_provider_health_breaker_schema` uses `CREATE TABLE IF NOT EXISTS` plus
  additive `ALTER TABLE ... ADD COLUMN` guarded by column-existence checks
  (`provider_health_breaker.py:42,105-116`).
- Test `test_production_state_additive_fixture_gets_new_tables` builds a pre-policy
  DB, asserts `containment_rate_counters`, `circuit_breaker_state`,
  `provider_health_metrics` are ABSENT before, then confirms all required tables
  PRESENT after production open. This proves the upgrade path actually adds tables
  (not merely that they pre-existed). PASSED.

### Criterion 3 — Incompatible schema version still rejects startup (PASS)

- `verify_schema_version` (`store.py:300-310`) raises `IncompatibleSchemaError`
  and runs at `store.py:346`, BEFORE `ensure_production_policy_tables`
  (`store.py:367-370`), so a bad version aborts before any table upgrade.
- Test `test_production_state_rejects_incompatible_schema_version` sets stored
  version to 999 and asserts `IncompatibleSchemaError` matching
  "incompatible state schema" on production open. PASSED.

### Criterion 4 — Verifier checks only V2-017 acceptance, not V2 Gate 3 (PASS)

- This verification was scoped strictly to the four criteria above. No V2 Gate 3
  exit or phase-completion checks were run or claimed.

## Command Output

```
$ python -m pytest tests/ -q -k "production_state or state_store or startup or policy_state"
......................................................                   [100%]
54 passed, 807 deselected in 4.95s
(exit code 0)

$ python -m pytest tests/runtime/test_production_state_init.py -v
tests/runtime/test_production_state_init.py::test_production_state_store_creates_required_policy_tables PASSED
tests/runtime/test_production_state_init.py::test_production_state_additive_fixture_gets_new_tables PASSED
tests/runtime/test_production_state_init.py::test_production_state_rejects_incompatible_schema_version PASSED
3 passed in 0.54s (exit code 0)
```

Independently reproduced the implementer's claimed "54 passed, 807 deselected".

## Skeptical Checks Attempted (all survived)

- Weakened/no-op assertion? No — `assert_production_policy_tables` raises on
  missing tables and is reachable only after `ensure_*` runs; removing the ensure
  wiring would break the entrypoint.
- Tables pre-existing so the upgrade test is vacuous? No — the additive test
  explicitly asserts absence before and presence after.
- Guard bypassed by table creation running first? No — `verify_schema_version`
  precedes `ensure_production_policy_tables` in `open_state_store`.
- Stale evidence? No — re-ran commands against current working tree.

## Gaps

None within V2-017 scope.
