# Active Context

## Current focus

**TASK-015 complete** — evidence citation validation is shared: `praetor.evidence.citations` validates cited evidence IDs and field paths against `EvidenceBundle`, requires citations for `escalate` / `auto_contain`, exposes cited fact `ambiguity_flag`, and the walking skeleton now delegates to it.

Next: **TASK-016** (canonical account identity and synthetic provenance tests).

## Recently changed

- TASK-015: `src/praetor/evidence/citations.py` and `tests/evidence/test_citation_validation.py` add the shared structural citation validator; `src/praetor/engine/citations.py` now adapts the walking skeleton to the shared path, with `src/praetor/engine/skeleton.py` providing an `EvidenceBundle` fixture.
- TASK-014: `src/praetor/judgment/excerpt.py` and `src/praetor/judgment/prompt.py` add 200-character head+tail prompt excerpts, recursive `raw_source` exclusion, incomplete-content warnings, verbatim org-config prompt payloads, and structured-output instructions.
- `src/praetor/engine/orchestrator.py` now builds `JudgmentRequest.payload` from sanitized prompt output (`prompt_excerpt_set`) instead of minimal hash-only Task 13 payloads; `config_over_budget` still blocks the provider before prompt construction.
- TASK-013: `src/praetor/judgment/` — shared `JudgmentProvider` Protocol, `JudgmentRequest`, `ProviderRetryPolicy`, typed provider failures, scenario-scoped FakeProvider modes (`valid`, `malformed_json`, `timeout`, `refusal`, `fabricated_citation`), and no-network `VertexProvider` stub.
- `src/praetor/engine/orchestrator.py` now calls the shared provider Protocol and maps `provider_malformed_json`, `provider_timeout`, and `provider_refusal` to `escalate` with `system_fault_escalation=true`; fabricated citations continue through citation validation.
- README updated with phase structure, Phase 1 status, built-so-far summary, and browse/demo guidance.
- Phase 1 punch-list cleared: live emergency records/revocations and activation revocations now append to the hash-chain ledger; guarded `open_state_store(..., singleton=...)` fails closed when the singleton/WAL guard is not satisfied; repo-wide ruff is clean.
- TASK-012: `src/praetor/engine/` — hardcoded bundle/judgment intake, fault paths (`correlation_failure`, `config_over_budget`, `invalid_model_citation`), `run_engine_startup_recovery` wired in `open_state_store`; no recovery `auto_contain`.
- TASK-011: revocation feed JSONL exporter, startup recovery hook, feed-health probes, smoke benchmark.
- TASK-010: hash-chained ledger, startup integrity hook.

## Current blockers

- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- PolicyGate not yet implemented (Task 17); skeleton policy inline only.
- Startup recovery step 6 is not implemented and is a hard prerequisite for Tasks 17-19.

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** substitute only via `engine/ids.py` / `decision_id_for_attempt`.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Startup order: singleton lock → SQLite guard → `open_state_store` (ledger verify, **engine recovery**, then feed recovery if active config) → intake.
7. Engine intake: `process_alert_intake` / `WalkingSkeletonEngine` after active org config; never emits `auto_contain` in v1 skeleton.
8. Provider layer: Task 14 request payload includes sanitized `prompt_excerpt_set`, verbatim org config, incomplete-content notice, and structured-output instructions. FakeProvider modes are scenario-scoped and no real Vertex call exists yet.
9. Citation validation: Task 15 shared validator lives in `src/praetor/evidence/citations.py`; unresolved evidence IDs/field paths and missing `escalate` / `auto_contain` citations are invalid. PolicyGate must reuse this validator when implemented.
10. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
