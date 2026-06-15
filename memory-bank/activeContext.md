# Active Context

## Current focus

**TASK-028 complete** — Windows Sysmon/Security normalization into `EvidenceBundle` + bounded `PromptExcerptSet`; process relationship graph; time-window filtering; fixture manifest registered.

Next: **TASK-029** (Correlator Identity Compliance Tests). Follow-on: **TASK-28a** wire PolicyGate + metrics into correlation-aware orchestrator.

## Recently changed

- TASK-028: `src/praetor/correlation/` — Sysmon EventID 1 + Security 4624 normalizers, ±300s window filter, process GUID graph, Task 14 excerpt bridge; 4 fixtures + manifest checksums; **9** correlation tests; suite **638**.
- TASK-027 gatekeeper reopen: payload-driven structural checks, truncated fixture, mocked Gemini tests (+7), mypy `evals` package (102 files), `docs/eval_gates.md` + DEC-047; **14** deterministic adversarial tests; eval suite **47**; full suite **629**.
- TASK-026 follow-up: `evals/outcome_matrix.py` — canonical SFE map from `OutcomeMatrixFaultFlag`; 24 scenarios (+10 matrix rows); completeness guard; fail-closed SFE; `ticket_stamp_failed` + `policy_gate_idempotency`; **33** eval tests; suite **615**.

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md` (Task 35). `docs/eval_gates.md` added in TASK-027.
- PolicyGate module complete but not wired into `engine/orchestrator.py` intake path (Task 28a / DEC-048).
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
12. Correlation: `correlate_telemetry()` in `praetor.correlation` produces bundle + `PromptExcerptSet`; orchestrator wiring deferred to Task 28a.
