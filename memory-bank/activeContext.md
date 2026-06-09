# Active Context

## Current focus

**TASK-017 complete** — Deterministic PolicyGate v1 lives in `praetor.policy.gate` with containment policy evaluation, directive building, durable rate/breaker/idempotency state, and startup recovery step 6 (`reconcile_policy_state`). Production callers should use `open_production_state_store` with a held `SingletonLock`.

Next: **TASK-018** (Transactional Rate Limits and Containment Breaker). Follow-on: wire PolicyGate into engine intake (orchestrator still uses skeleton inline policy).

## Recently changed

- TASK-017: `src/praetor/policy/{gate,containment_policy,directive_builder,state}.py` — PolicyGate v1, step 6 reconciliation, `open_production_state_store`; `tests/policy/` (21 tests).
- TASK-016: `src/praetor/evidence/provenance.py` and `src/praetor/policy/identity.py` add corroboration and account containment eligibility; synthetic fixtures and tests.
- TASK-015: shared citation validator in `src/praetor/evidence/citations.py`.
- TASK-014: prompt construction and excerpt hygiene in `src/praetor/judgment/`.
- TASK-013: judgment provider Protocol and FakeProvider modes.
- Phase 1 punch-list cleared; repo-wide ruff clean.
- TASK-012: walking skeleton engine with startup recovery steps 4–5–7 (now includes step 6 via TASK-017).

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- PolicyGate module complete but not wired into `engine/orchestrator.py` intake path.
- v1 rate-limit ceiling is fixed until Task 18 org-config sliding windows land.

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** substitute only via `engine/ids.py` / `decision_id_for_attempt`.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Startup order: singleton lock → SQLite guard → `open_state_store` (ledger verify, **engine recovery incl. step 6**, then feed recovery if active config) → intake.
7. Engine intake: `process_alert_intake` still uses skeleton inline policy; call `evaluate_policy_gate` when wiring containment.
8. Citation validation: Task 15 shared validator in `src/praetor/evidence/citations.py`; PolicyGate reuses it.
9. Account identity: Task 16 evaluator + Task 17 `account_containment_disabled` feature gate in PolicyGate.
10. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
