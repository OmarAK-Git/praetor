# Review: TASK-009 (third reopen — gate open)

## Status

Verification commands pass (55 config / 254 full). **Task not closed** pending operator sign-off.

## Third-reopen fixes (local gaps)

| # | Gap | Resolution |
|---|-----|------------|
| 1 | Stale workflow / Memory Bank | Artifacts updated to 49/248 evidence and current contract decisions |
| 2 | Quoted policy integers | Pre-Pydantic `_require_positive_int` + `StrictInt` on policy models |
| 3 | `CanonicalSerializationError` leak | Wrapped in `compute_snapshot_hash_from_binding` → `PreflightError.invalid_binding_value` |
| 4 | Fetch ignored JSON `snapshot_hash` field | Reject field mismatch + `verify_snapshot_hash` on fetch |
| 5 | Same hash dropped second verbatim | `org_config_verbatim_renders` + active `verbatim_render_id` |
| 6 | Health flush non-recoverable / duplicate IDs | Stable pending `alert_id`; `drain_unflushed_health_alerts` before activation/emergency |

## Prior reopen (retained)

Immutable snapshots, lock boundaries inside `critical_transaction`, canonical emergency targets, public surface trimmed, emergency retirement on activation.

## Deferred

- Hash-chained ledger interleave (Task 10)
- Intake-time `config_over_budget` PolicyGate (Task 12)
- Repo-wide `ruff check` E501 outside TASK-009 paths

## Sign-off

**Not safe to commit** as formal TASK-009 completion until operator closes the reopen. Evidence: `verification.md`.
