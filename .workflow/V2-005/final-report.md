# Final Report — V2-005

## Summary

Implemented **v2_hardening Item 2a**: strict `ContainmentRule` / `ContainmentPolicy` schema with typed `scope` union (target, asset, catch-all), `extra="forbid"`, preflight rejection of malformed scopes (`invalid_containment_rule_scope`), and gate evaluation of catch-all rules without silent skip. Example org config and sweep template use `{ catch_all: true }` instead of invalid `scope: global`.

**Reopen (2026-06-29):** ruff E501 line-wrap fix in `containment_policy.py`; parametrized negative test for malformed object scopes (`catch_all: false`, mixed keys). Full VS-0001 gate green.

**V2 Gate 1 in progress** (V2-005 closed; V2-006 not started).

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 String/malformed scope fails preflight | `invalid_containment_rule_scope`; string + object-scope tests |
| REQ-002 Unknown keys rejected | `extra="forbid"` on containment models; preflight + tests |
| REQ-003 Scope round-trip | `test_containment_rule_scopes_round_trip` |
| REQ-004 Example config valid | `configs/example_org.yaml`; hash `b91161d3…` |
| REQ-005 No silent scope skip | `_rule_scope_matches_target` + `test_catch_all_scope_matches_any_target` |

## Files changed (initial + reopen)

- `src/praetor/contracts/org_config_sections.py` — scope models, strict ContainmentRule/Policy
- `src/praetor/config/preflight.py` — `_validate_containment_policy`, scope error codes
- `src/praetor/policy/containment_policy.py` — typed scope matching incl. catch-all; ruff E501 wrap
- `configs/example_org.yaml` — `catch_all: true`
- `src/praetor/codification/sweep.py` — sweep template scope fix
- `tests/config/test_org_config_loader.py` — scope negative/round-trip tests incl. `test_malformed_object_scope_fails_preflight`
- `tests/config/test_config_gate.py` — activation string-scope test
- `tests/config/shared.py` — `EXAMPLE_SNAPSHOT_HASH`
- `tests/policy/test_containment_policy.py` — catch-all match test
- `tests/policy/test_rate_limits.py`, `test_containment_circuit_breaker.py` — valid scopes
- `.workflow/V2-005/*`, `memory-bank/{tasks,activeContext,progress}.md`

## Verification performed (VS-0001, 2026-06-29 reopen)

```
python -m pytest -q
python -m mypy src evals consumer_sdk
python -m ruff check src tests evals consumer_sdk
```

| Check | Result |
|---|---|
| pytest | **793 passed**, 2 deselected, 1 xfailed |
| mypy | **118** source files, no issues |
| ruff | All checks passed |
| String scope | `test_string_scope_global_fails_preflight` pass |
| Object scope | `test_malformed_object_scope_fails_preflight` (2 cases) pass |
| Unknown keys | `test_unknown_containment_rule_key_rejected` pass |
| Round-trip | `test_containment_rule_scopes_round_trip` pass |
| Catch-all gate | `test_catch_all_scope_matches_any_target` pass |

## Known gaps

- Escalate blocking and `default_action` deferred to V2-006/V2-012/V2-013 (not started).
- `docs/` not updated (task constraint).

## safe_to_commit

yes — 2026-06-29 reopen verification green (VS-0001 full gate)
