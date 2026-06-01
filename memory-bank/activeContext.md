# Active Context

## Current focus

**TASK-004 next** — authenticated write surface primitives (`docs/plan.md` Task 4). TASK-003 complete (including doc-first contract corrections).

**Hard gate:** Three role-tagged external surfaces; ledger/feed/directive emission remain internal-only.

## Recently changed

- **`docs/contracts.md`:** new §5 `stamp_id` (three-tuple, stable across attempts); §7 `EMPTY_BUNDLE` preimage `praetor:v1:empty_bundle`; sections renumbered §6–§15.
- TASK-003: `src/praetor/hashing/` aligned to updated contracts; `tests/hashing/`.
- Flight Recorder: `.workflow/TASK-003/` complete.

## Current blockers

- None for Task 4 start.
- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- Provisional alert-rate targets — **TODO** before Sprint 1 ends (Tasks 9 / 11).

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** preimage exactly `praetor:v1:empty_bundle`; hash baked into correlation-failure IDs.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code — not follow-up tickets.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Domain constants live only in `src/praetor/hashing/domains.py`.
7. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
