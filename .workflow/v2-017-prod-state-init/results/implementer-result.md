# Implementer Result — V2-017 Production State Initialization Guard

implementation_model: composer-2.5-fast

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/policy/state.py` | Added `REQUIRED_PRODUCTION_POLICY_TABLES`, `ensure_production_policy_tables`, and `assert_production_policy_tables`; consolidated reconcile init into `ensure_production_policy_tables`. |
| `src/praetor/state/store.py` | Production singleton path calls `ensure_production_policy_tables` before engine recovery so policy tables are created/upgraded without caller `init_*` calls. |
| `src/praetor/runtime/startup.py` | `open_production_state_store` asserts required tables after open (lazy import to avoid circular import via `runtime.__init__`). |
| `tests/runtime/test_production_state_init.py` | New V2-017 tests for table creation, additive fixture upgrade, and incompatible schema rejection. |

## How production table initialization is enforced

1. **Ensure on open (production path):** When `open_state_store` is called with a held `SingletonLock`, it invokes `ensure_production_policy_tables`, which runs `init_policy_state_schema` (`CREATE TABLE IF NOT EXISTS` for rate counters and circuit breakers) and `init_provider_health_breaker_schema` (additive `ALTER TABLE` columns plus `provider_health_metrics` table).
2. **Assert at production entrypoint:** `open_production_state_store` calls `assert_production_policy_tables` after open to fail closed if any of the five required tables (`analyst_annotations`, `containment_rate_counters`, `circuit_breaker_state`, `provider_health_metrics`, `revocation_feed_export_meta`) are missing.
3. **Reconcile reuses ensure:** `reconcile_policy_state` (startup step 6) now calls `ensure_production_policy_tables` instead of duplicating manual `init_*` calls.
4. **Schema version guard unchanged:** `verify_schema_version` in `open_state_store` still rejects incompatible `schema_meta.schema_version` before recovery proceeds.

## Test additions

- `test_production_state_store_creates_required_policy_tables` — held singleton open creates all five required tables without manual `init_*`.
- `test_production_state_additive_fixture_gets_new_tables` — pre-policy DB fixture upgraded via production open (`CREATE TABLE IF NOT EXISTS`).
- `test_production_state_rejects_incompatible_schema_version` — stored schema version 999 raises `IncompatibleSchemaError` on production open.

## Verification command output

```
pytest tests/ -q -k "production_state or state_store or startup or policy_state"
......................................................                   [100%]
54 passed, 807 deselected in 6.06s
```

**Result: PASS**

## Approval gates hit

None.
