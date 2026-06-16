# Active Context

## Current focus

**Phase 3 gate CLOSED (PASS-WITH-CONDITIONS)** — `.workflow/phase-3-gate-punchlist.md` (705 passed, 1 deselected, 1 xfailed; harness 26/26; phase3 gate 6/6; correlation 5/5; tripwires 3/3).

Next: **TASK-032** (Sigma Rule Packaging) — Sprint 4 / Phase 4.

## Recently changed

- Phase 3 gate verification: independent re-run of all mechanical checks; DEC-053 ratified (deferred directive persist); README reconciled to Phase 3 state.
- TASK-031 / DEC-052: citation-anchored host targeting; phase 3 noisy gate GREEN; REVIEW-004 strict xfail tracked.
- TASK-030: `evals/correlation_gate.py` — 5 CLI scenarios; 19 tests.
- TASK-028a: PolicyGate + metrics on intake; tripwires converted to passing.

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md` (Task 35). `docs/eval_gates.md` added in TASK-027.
- Sprint 4 scaffolding absent: no `detections/` tree until Task 32.

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** substitute only via `engine/ids.py` / `decision_id_for_attempt`.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Startup order: singleton lock → SQLite guard → `open_state_store` (ledger verify, **engine recovery incl. step 6**, then feed recovery if active config) → intake.
7. Stamp contract: failure preserves full candidate row + appends `ticket_stamp_failed`; in-flight (`pending`/`unknown`) defers ledger append; redelivery raises `ActiveAttemptExistsError` (DEC-043).
8. Provider latency SLA: DEC-039 end-to-end retry loop timing; v1 provisional constant 30s.
9. Rate limits: DEC-029 limit=1/scope/window; DEC-030 `per_asset_group` = host asset_id only.
10. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
11. Eval harness: `python -m evals.harness` runs all mandatory scenarios; exits non-zero on any safety invariant failure.
12. Correlation: `correlate_telemetry()` in `praetor.correlation`; intake uses bundle override or telemetry params.
13. Intake: `process_alert_intake` runs `evaluate_policy_gate(..., persist_directive=False)`; directive + edict co-commit after terminal stamp (DEC-053).
14. Phase 3 gate: `python -m evals.run_phase3_gate` — correlation expected file, identity compliance, account prerequisite, citation-anchored safety on noisy bundle, Phase 2 harness.
15. Host containment (DEC-052): target derived from **cited** facts only; ≥2 distinct quoted hosts → `ambiguous_containment_target`.
