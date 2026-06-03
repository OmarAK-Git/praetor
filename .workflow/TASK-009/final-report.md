# Final Report: TASK-009 (third reopen — not closed)

## Status

**Reopen verification passed; task not marked complete** per user directive.

## Source decisions (conflicts resolved)

| Topic | Authority | Decision |
|-------|-----------|----------|
| Judgment render vs binding hash | `docs/contracts.md` §3a (updated) | Verbatim UTF-8 source for budget/render; canonical binding body for `snapshot_hash` |
| Account auto-contain | `docs/spec.md`, contracts §Account gate | Omitted → default `false`; `true` rejected at preflight (no self-attested Phase 3) |
| Emergency target shape | `docs/spec.md` § account targets | Canonical `{target_type, target_id}` only; account `target_id` must be SID |
| External write surfaces | `docs/spec.md` §281–287 | `persist_org_config_snapshot` / `purge_expired_emergency_records` removed from public `praetor.config` |
| Health alerts | Implementation | Queued in `critical_transaction`, flushed via `health_alert_pending_flush` with retry |

## Deliverables

- `src/praetor/config/` — loader with verbatim text, preflight, snapshot integrity, activation/emergency lock boundaries, durable health queue
- `tests/config/` — 49 tests including `test_config_gate.py`
- `docs/contracts.md` — test vector hash updated to match `example_org.yaml` (no `phase_3_identity_gates_passed`)

## Verification (2026-06-03)

```
pytest -q tests/config/     → 55 passed
pytest -q                   → 254 passed
mypy src                    → OK
ruff check src/praetor/config tests/config tests/contracts/test_org_config_contract.py → OK
ruff check (VERIFY-004b cross-cutting paths in verification.md) → OK
```

## Remaining for formal close

- Human sign-off on reopen findings 1–17
- Optional: repo-wide ruff cleanup (outside TASK-009 scope)
