# Implementer Result — V2-026 Org-Config Numeric Rate Ceilings

implementation_model: composer-2.5-fast

## Summary

Replaced DEC-029's fixed per-scope ceiling (`limit=1`) with org-configurable numeric ceilings on `rate_limit_policy.ceilings` for `per_host`, `per_subnet`, and `per_asset_group`. Preflight applies strict positive-integer validation and fills missing ceiling keys with the documented default (`1`). PolicyGate enforcement reads per-scope ceilings from the active snapshot via `scope_event_ceiling()`.

## Files Changed

| File | Rationale |
|---|---|
| `src/praetor/contracts/org_config_sections.py` | Added `RateLimitCeilings` model and `ceilings` field on `RateLimitPolicy` |
| `src/praetor/config/preflight.py` | Default/missing ceiling application, strict integer validation, unknown-key rejection |
| `src/praetor/policy/rate_limit.py` | Per-scope ceiling lookup; removed fixed `DEFAULT_SCOPE_EVENT_LIMIT` parameter |
| `tests/config/test_rate_limit_ceilings.py` | Preflight default, partial, invalid, and explicit ceiling tests |
| `tests/config/shared.py` | Re-pinned `EXAMPLE_SNAPSHOT_HASH` after ceilings added to snapshot binding |
| `tests/policy/test_rate_limits.py` | Configurable host/subnet ceiling gate enforcement tests |
| `memory-bank/decisions.md` | Updated DEC-029 to reflect V2-026 configurable semantics |

## Test Additions

- `test_preflight_applies_default_ceilings_when_missing`
- `test_preflight_applies_default_for_partial_ceilings`
- `test_preflight_rejects_invalid_ceiling_values` (parametrized)
- `test_preflight_rejects_unknown_ceiling_scope`
- `test_preflight_accepts_explicit_ceilings`
- `test_configured_per_host_ceiling_allows_n_events`
- `test_configured_subnet_ceiling_blocks_third_host`

## Verification Output

```text
$ pytest tests/config/ tests/policy/test_rate_limits.py -q
........................................................................ [ 85%]
............                                                             [100%]
84 passed in 7.34s
```

## Approval Gates

- Queue item **not** marked done (per implementer packet).
- V2 Gate 4 exit **not** run (per implementer packet).
- Scope limited to allowed files; `configs/example_org.yaml`, `schemas/`, and `codification/sweep.py` untouched (defaults applied at preflight).

## Unresolved

- `EXAMPLE_SNAPSHOT_HASH` re-pin will cascade to engine/ticket tests outside this verification scope; full suite should be run before merge.
- `configs/example_org.yaml` and sweep template still omit explicit `ceilings`; preflight defaults preserve activatability but explicit YAML documentation is deferred.
