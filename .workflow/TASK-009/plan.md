# Plan: TASK-009 (third reopen — not closed)

## Goal

Deliver **Org Config Loader, Preflight, Snapshot Binding, and Emergency Never-Contain** per `docs/plan.md` Task 9 and `docs/spec.md` § Org Config / Never-Contain / Emergency Entries.

**Authority:** `docs/spec.md`, `docs/plan.md` Task 9, `docs/contracts.md` §3a/§11 (including in-task §3a amendments for verbatim render, hash integrity, account gate).

## Scope

**In scope:**

- `src/praetor/config/*`, `configs/example_org.yaml`, `tests/config/*`
- `docs/contracts.md` §3a only (hash vector, verbatim render binding, integrity rules) — coordinated with code
- Flight Recorder + Memory Bank (evidence-aligned, gate open)

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| Hash-chained ledger append | Task 10 |
| PolicyGate / walking skeleton | Task 12+ |
| Full prompt rendering at intake | Task 12/14 |
| Feed exporter / startup recovery | Task 11–12 |
| Unrelated `docs/` sections | Outside §3a contract pins |

## Current contract decisions (third reopen)

- Verbatim judgment render = UTF-8 source file; budget = Unicode length of source.
- Binding hash = canonical typed body (`ORG_CONFIG_SNAPSHOT_HASH_KEYS`).
- Verbatim stored per `(snapshot_hash, verbatim_render_id)`; active activation records render id.
- `account_auto_contain_enabled=true` rejected in v1; no Phase 3 self-attest in org config.
- Policy integers: strict `int` (no quoted-number coercion).
- Health alerts: stable `alert_id` in pending queue; `drain_unflushed_health_alerts` on activation/emergency.

## Verification plan

- `pytest -q tests/config/` → 55 passed
- `pytest -q` → 254 passed
- `mypy src`
- `ruff check src/praetor/config tests/config tests/contracts/test_org_config_contract.py`
