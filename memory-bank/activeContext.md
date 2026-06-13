# Active Context

## Current focus

**TASK-026 complete (matrix-hardened)** — 24 scenario fixtures cover all escalate-producing Outcome Matrix rows; canonical `OutcomeMatrixFaultFlag` SFE guard; `ticket_stamp_failed` + policy-gate idempotency scenarios.

Next: **TASK-027** (Real-Provider Adversarial Excerpt Probe). Follow-on: wire PolicyGate into engine intake; wire `MetricsCollector` into intake/export paths.

## Recently changed

- TASK-026 follow-up: `evals/outcome_matrix.py` — canonical SFE map from `OutcomeMatrixFaultFlag`; 24 scenarios (+10 matrix rows); completeness guard; fail-closed SFE; `ticket_stamp_failed` + `policy_gate_idempotency`; **33** eval tests; suite **615**.
- TASK-026: `evals/harness.py` + `evals/scenarios/*.yaml` — 14 mandatory scenarios, JSON schema validation, engine/policy_gate/prompt/duplicate/revocation_feed runners; 19 eval tests; suite **601**.
- TASK-025: `annotations/store.py` — SQLite `analyst_annotations` table, `submit_annotation` with Task 4 auth; 8 annotation tests; suite **578**.
- TASK-024: `metrics/{collector,events}.py` — in-process metrics collector with independent breaker/probe domains, feed lag p99 + unhealthy transitions; 13 metrics tests; suite **556**.

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- PolicyGate module complete but not wired into `engine/orchestrator.py` intake path (eval harness exercises gate directly).
- Metrics collector not wired into production call sites; no intake/UI surface for annotation submission.

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
11. Eval harness: `python -m evals.harness` runs all 14 mandatory scenarios; exits non-zero on any safety invariant failure.
