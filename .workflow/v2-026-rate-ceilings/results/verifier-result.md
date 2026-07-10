# Verifier Result — V2-026 Org-Config Numeric Rate Ceilings

verifier_model: composer (skeptic-verifier subagent)
scope: task-scoped only (NOT V2 Gate 4)
verdict: **SURVIVES** (claim of completion not refuted)

## Claim Under Test

"V2-026 done: org config declares numeric per-scope ceilings with strict integer
validation; gate enforces configured ceilings for host/subnet/asset-group;
missing/invalid ceilings fail preflight or apply documented defaults consistently.
84 tests pass."

## Fresh Verification Evidence

### Command (re-run independently, not from implementer transcript)

```text
$ python -m pytest tests/config/ tests/policy/test_rate_limits.py -q
........................................................................ [ 85%]
............                                                             [100%]
84 passed in 7.26s
(exit code 0)
```

Matches implementer's reported 84 passed. No skips/xfails in output.

### AC1 — numeric per-scope ceilings + strict integer validation — CONFIRMED

- `RateLimitCeilings` (`src/praetor/contracts/org_config_sections.py:77-80`) declares
  `per_host`/`per_subnet`/`per_asset_group` as `StrictInt` with `gt=0`.
- Preflight `_validate_rate_limit_ceilings` (`config/preflight.py:261-284`) rejects
  unknown scope keys and runs `_require_positive_int` (rejects non-`int` type incl.
  quoted strings/floats/bool, and non-positive) with code `invalid_rate_limits`.
- Independent adversarial probe of the model layer:
  ```text
  RateLimitCeilings(per_host=<bad>...) -> rejected True, '2', 1.5, 0, -1 (ValidationError)
  ```
  Both the pydantic layer and the preflight layer reject non-integers/non-positive.

### AC2 — gate enforces configured ceilings for host/subnet/asset-group — CONFIRMED

- `is_rate_limit_exceeded_for_target` (`policy/rate_limit.py:145-164`) compares each
  applicable scope's count against `scope_event_ceiling(snapshot, scope.scope_name)`,
  which is `int(getattr(ceilings, scope_name))` — a uniform per-scope read, no fixed
  literal.
- The old fixed `DEFAULT_SCOPE_EVENT_LIMIT` / `limit=1` is fully removed (repo-wide grep: no matches).
- Tests genuinely exercise the NEW config path (not gamed): `test_configured_per_host_ceiling_allows_n_events` sets `per_host=2` and asserts 2 events allowed then 3rd blocked; `test_configured_subnet_ceiling_blocks_third_host` sets `per_subnet=2`, `per_host=99` and asserts the 3rd host blocked on subnet. Against the previous fixed `limit=1` these tests would fail on the 2nd event — so they truly bind to configured ceilings.
- Asset-group lookup proven directly: `getattr(ceilings,'per_asset_group') -> 9` for a
  configured value; enforcement of the `per_asset_group` scope path is exercised by
  `test_per_asset_group_scope_collapses_to_per_host_for_v1`.

### AC3 — missing/invalid fail preflight OR documented defaults consistently — CONFIRMED

- Missing `ceilings`: preflight fills all scopes with `DEFAULT_RATE_LIMIT_SCOPE_CEILING = 1`
  (`test_preflight_applies_default_ceilings_when_missing`).
- Partial `ceilings`: unspecified scopes defaulted to 1 (`test_preflight_applies_default_for_partial_ceilings`).
- Invalid values and unknown scope keys raise `PreflightError(invalid_rate_limits)`
  (`test_preflight_rejects_invalid_ceiling_values`, `test_preflight_rejects_unknown_ceiling_scope`).
- Default documented consistently: `memory-bank/decisions.md:35` DEC-029 states default = 1
  event per scope when omitted; matches both `preflight.DEFAULT_RATE_LIMIT_SCOPE_CEILING`
  and `_default_rate_limit_ceilings()` model default.

## Attempts to Refute (all failed to break the claim)

- Checked for gamed/weakened tests: configured-ceiling tests use values >1, which would
  break against the removed fixed limit — not gamed.
- Checked for stale evidence: re-ran the command fresh; no reliance on transcript.
- Checked for orphaned old constant: `DEFAULT_SCOPE_EVENT_LIMIT`/`limit=1` gone repo-wide.
- Checked strict-integer intent vs letter: both preflight and pydantic reject bool/str/float.

## Non-Refuting Observations (minor, out of task scope)

- No dedicated gate test sets a **non-default** `per_asset_group` ceiling (host and subnet
  each get one). Asset-group enforcement is nonetheless proven via the uniform per-scope
  lookup + the existing `per_asset_group` enforcement test. Not a functional gap.
- `configs/example_org.yaml` and the sweep template omit explicit `ceilings`; preflight
  defaults preserve activatability (implementer-noted deferral; outside verification scope).
- Implementer notes `EXAMPLE_SNAPSHOT_HASH` re-pin cascades to engine/ticket tests outside
  this scope — full suite should run before merge/Gate. Not evaluated here (task-scoped).

## Verdict

**SURVIVES.** All three acceptance criteria hold under independent verification; the scoped
command passes 84/84 with exit 0; the enforcement path is demonstrably configurable per
scope; validation and defaults behave as documented. Completion claim is not refuted.
