# V2 Gate 3 Exit — Production Hardening (phase_exit gate)

## Goal (verbatim)

V2 Gate 3 exit (PASS-only): production hardening sprint complete per
`docs/proposals/v2_implementation_plan.md` § V2 Gate 3.

## Run mode

`chat_gate` / `verification.scope: phase_exit`. Verify-only, run inline in this
chat with the UI-selected model. No implementation. No subagent dispatch.

## Scope

Full V2 Gate 3 exit verification only. No new implementation; confirm pass
criteria for V2-017 through V2-023. Files allowed: `.workflow/v2-gate-3-exit/`,
`memory-bank/progress.md`, `memory-bank/activeContext.md`, `memory-bank/tasks.md`.

## Dependencies (all `done`)

- v2-017-prod-state-init
- v2-018-revocation-feed
- v2-019-ledger-feed-floor
- v2-020-metrics-completeness
- v2-021-evidence-id
- v2-022-sid-normalizer
- v2-023-scope-guard

## Acceptance criteria (per plan § V2 Gate 3)

1. Production startup initializes required tables (V2-017).
2. Revocation/feed semantics are consumer-verifiable (V2-018).
3. Ledger/feed integrity limits are guarded or operator-visible (V2-019).
4. Metrics are wired from real completion points (V2-020).
5. Evidence IDs are contract-pinned (V2-021).
6. SID/normalizer conformance is tested (V2-022).
7. Scope/schema guards remain strict (V2-023).
8. Full pytest, ruff, and mypy pass.

## Verification commands

- `python -m pytest -q`
- `python -m ruff check .`
- `python -m mypy .`

## Tier

T2 (phase exit gate).
