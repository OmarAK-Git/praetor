# Active Context

## Current focus

**TASK-005 next** — SQLite startup guard and process singleton (`docs/plan.md` Task 5). TASK-004 complete.

**Hard gate:** Three role-tagged external surfaces exist; ledger/feed/directive emission remain internal-only.

## Recently changed

- TASK-004: `src/praetor/auth/` — `Principal`, `TokenVerifier`, three authenticated write surfaces.
- Flight Recorder: `.workflow/TASK-004/` complete.
- **`docs/contracts.md`:** §5 `stamp_id`; §7 `EMPTY_BUNDLE` preimage (TASK-003).

## Current blockers

- None for Task 5 start.
- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- Provisional alert-rate targets — **TODO** before Sprint 1 ends (Tasks 9 / 11).

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** preimage exactly `praetor:v1:empty_bundle`; hash baked into correlation-failure IDs.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code — not follow-up tickets.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Domain constants live only in `src/praetor/hashing/domains.py`.
7. Auth: external surfaces via `authenticate_*` functions; token issuance is operator-supplied (`TokenVerifier` protocol).
8. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
