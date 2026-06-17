# Active Context

## Current focus

**TASK-035 complete** — production throughput benchmark + operator runbooks; pytest **778**. All **35** plan tasks complete.

## Recently changed

- TASK-035: `benchmarks/serialized_path.py`, `docs/operator_runbook.md`, `docs/architecture.md`, `tests/docs/test_docs.py`; contracts §15 throughput; eval_gates phase gates; scope guard Phase 5 docs.
- TASK-034: `src/praetor/codification/` — telemetry sweep, proposed artifact, coverage/risk report; preflight blocks activation; **17** codification tests.
- TASK-033: SPL compile + Splunk demo harness; **21** splunk tests.
- Phase 3 gate closed PASS-WITH-CONDITIONS; DEC-053 ratified.

## Current blockers

- None for plan tasks. Live Splunk HEC demo remains operator-driven (env-gated test).

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
16. SPL compile: `python tools/compile_sigma.py --check`; Splunk demo steps in `splunk/README.md`.
17. Org-config sweep: `run_org_config_sweep()` in `praetor.codification`; proposed artifacts carry `artifact_kind: proposed_org_config` and are rejected by preflight.
18. Production benchmark: `benchmarks/serialized_path.py`; throughput ceiling in `docs/operator_runbook.md`.
19. Operator docs: `docs/operator_runbook.md`, `docs/architecture.md`, phase gates in `docs/eval_gates.md`.
