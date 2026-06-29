# Progress Log

## 2026-06-29 — V2-008 complete (Gate 1 continued, parallel branch)

- **DEC-053 compound fault fidelity:** stamp `FAILED` + `DeferredDirectivePersistConflict` preserves both conflict fault flag and `ticket_stamp_failed`; fail-closed escalate with directive suppressed unchanged.
- Orchestrator conflict path already re-applies `apply_terminal_stamp_to_disposition` on HEAD; added contract unit test `test_stamp_failure_appends_flag_after_deferred_persist_conflict_escalation`.
- Integration coverage: `test_failed_stamp_and_deferred_persist_conflict_preserves_both_fault_flags` (existing).
- Closed DEC-053 known-fidelity-gap note in `memory-bank/decisions.md`.
- Isolated worktree: `.worktrees/V2-008` on branch `task/V2-008`.
- Flight Recorder: `.workflow/V2-008/`.
- Verification: VS-0001 (counts recorded in verification.md).

## 2026-06-29 — V2-005 complete (Gate 1 started)

- **v2_hardening Item 2a:** typed `ContainmentRule.scope` (target / asset / catch-all), `extra="forbid"` on containment models, preflight `invalid_containment_rule_scope` for string scopes, gate catch-all matching.
- Updated `configs/example_org.yaml` (`catch_all: true`), `EXAMPLE_SNAPSHOT_HASH`, sweep template.
- Tests: 4 config loader, 1 config gate, 1 containment policy; policy test scope fixes.
- **Reopen:** ruff E501 wrap in `containment_policy.py`; `test_malformed_object_scope_fails_preflight` (`catch_all: false`, mixed keys); VS-0001 full gate green (pytest **793**, mypy **118**, ruff clean).
- Flight Recorder: `.workflow/V2-005/`.
- Verification: pytest **791** passed, 2 deselected, 1 xfailed.
- Follow-on: V2-006 escalate blocking; V2-012 `default_action`; V2-013 posture flip.

## 2026-06-29 — V2-004 complete (Gate 0 closed)

- Ratified **DEC-061**: `provider_unavailable` Outcome Matrix row (`escalate`, `system_fault_escalation=true`); distinct from `provider_timeout`, `provider_refusal`, `provider_health_breaker_open`; breaker tripping unchanged.
- Updated `docs/contracts.md` §13, `docs/decisions.md`, `docs/proposals/delivery_backlog.md`.
- Code: `OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE`, `LLM_FAILURE_FAULT_FLAGS`, `evals/outcome_matrix.py`, `FakeProviderMode.UNAVAILABLE`, orchestrator catch, harness scenario `provider_unavailable.yaml`.
- Tests: `tests/evals/test_provider_unavailable_matrix.py` (3), `test_provider_unavailable_escalates`.
- Flight Recorder: `.workflow/V2-004/`.
- Verification: pytest **785** passed, 2 deselected, 1 xfailed.
- **V2 Gate 0 closed** (V2-001 – V2-004). Follow-on: V2-007 metrics/breaker intake tests.

## 2026-06-29 — V2-003 reopen (snapshot_content timing)

- Corrected DEC-060 / `docs/contracts.md` §7a: `snapshot_content` is gate-evaluation capture on intake (not commit-time re-read as default); conflict rebuild paths may refresh; commit-time-only capture marked as follow-on implementation work.
- Flight Recorder: `.workflow/V2-003/` review/verification/final-report updated.
- Verification: pytest **785**; DEC-060 grep pass. No code or behavioral test changes.

## 2026-06-29 — V2-003 complete

- Ratified **DEC-060**: `NeverContainSnapshotRecord` engine-only append paired with `DecisionEdict`; expired re-issue retains §4.2 carve-out (no revocation record); expired-unrevoked rows excluded from step 6; orphan directives skipped + health surfacing deferred to V2-010.
- Updated `docs/contracts.md` §4.2.1/§7a, `docs/decisions.md`, `docs/proposals/delivery_backlog.md`.
- Flight Recorder: `.workflow/V2-003/`.
- Verification: pytest green (no code changes); DEC-060 grep checks pass.
- Implementation deferred to V2-009, V2-010, V2-018.

## 2026-06-29 — V2-002 complete

- Ratified **DEC-059**: host corroboration floor; `insufficient_corroboration` Outcome Matrix row; provenance trust classification (`sysmon_event_log` attacker-controllable, `windows_security_log` not); future paths default attacker-controllable; account `ambiguous_target_identity` unchanged.
- Updated `docs/contracts.md` §12a/§13, `docs/decisions.md`, `docs/proposals/v2_hardening.md`, `docs/proposals/delivery_backlog.md`.
- Flight Recorder: `.workflow/V2-002/`.
- Verification: pytest green (no code changes); DEC-059 grep checks pass.
- Implementation deferred to V2-011.

## 2026-06-29 — V2-001 complete

- Ratified **DEC-058**: deployment-configurable required `default_action`; v1 default-allow retired as drift; `escalate` blocks containment; rule-action and precedence semantics documented.
- Updated `docs/decisions.md`, `docs/proposals/v2_hardening.md`, `docs/proposals/delivery_backlog.md`.
- Flight Recorder: `.workflow/V2-001/`.
- Verification: pytest **780**, decision grep checks pass.
- No code changes (implementation deferred to V2-005, V2-006, V2-012, V2-013).

## 2026-06-29 — V2 Memory Bank initialized

- Indexed **36** V2 tasks from `docs/proposals/v2_implementation_plan.md` into `memory-bank/tasks.md`.
- Sprint groupings V2-0 through V2-5, full dependency index, **6** phase gates, and V1 carry-forward items recorded.
- `activeContext.md` updated: current focus Sprint V2-0 (V2-001 – V2-004); build order and governing constraints summarized.
- V1 history preserved under **Done (V1)** in tasks.md; pytest baseline **778** at TASK-035 close.
- No V2 implementation started; all V2 tasks status **pending**.

## 2026-06-16 — TASK-035 complete

- Production benchmark: `benchmarks/serialized_path.py` — PolicyGate emit + ledger append + revocation feed outbox vs `provisional_alert_rate_targets`.
- Operator docs: `docs/operator_runbook.md`, `docs/architecture.md`; `docs/contracts.md` §15; `docs/eval_gates.md` phase gates.
- Tests: `tests/benchmarks/test_serialized_path.py` — **3**; `tests/docs/test_docs.py` — **9**; scope guard allows Phase 5 docs.
- Splunk: env-gated `test_splunk_demo_integration_with_hec_env`; README/splunk README HEC notes.
- Verification: suite **778**, mypy **118** files, ruff OK.
- Flight Recorder: `.workflow/TASK-035/`.
- **All 35 plan tasks complete.**

## 2026-06-16 — TASK-034 complete

- Empirical org-config sweep: `src/praetor/codification/` — `run_org_config_sweep`, proposed artifact builder, coverage/risk report.
- Preflight: `proposed_artifact_not_activatable` for `artifact_kind: proposed_org_config`.
- Tests: `tests/codification/test_sweep.py` — **5**; scope guard allows `codification` package.
- Verification: codification **5/5**, suite **749**, mypy **116** files, ruff OK.
- Flight Recorder: `.workflow/TASK-034/`.

## 2026-06-16 — TASK-033 complete

- SPL compilation: `tools/compile_sigma.py` — pySigma Splunk backend + Windows pipeline; `--check` / `--write`.
- Artifacts: `detections/spl/*.spl` (5), `splunk/savedsearches.conf`, `splunk/props.conf`, `splunk/README.md`.
- Ingest: `tools/splunk_ingest_demo.ps1` — manifest path + sha256 validation; optional HEC ingest with flattened EventData + WinEventLog `source`.
- Tests: `tests/splunk/test_savedsearch_generation.py` — **21** (+1 integration deselected); `pysigma-backend-splunk>=1.1,<3`.
- Hardening (abaa724): correlation YAML rejection tests, `props.conf` stanza parse test, savedsearch source dedup test.
- Verification: splunk **21/21**, compile `--check` OK, suite **744**, mypy **112** files, ruff OK.
- Flight Recorder: `.workflow/TASK-033/`.

## 2026-06-16 — TASK-032 complete

- Sigma rule repository: `detections/sigma/windows/` — **5** rules (cmd, powershell -enc, notepad, calc, Security 4624); `detections/attack_mapping.yaml`.
- Tests: `tests/detections/test_sigma_rules.py` — **18**; pySigma parse/compile/validation; discrimination, tag↔mapping parity, manifest gate.
- Tooling: `pysigma>=1.3` dev dependency.
- Verification: detection **18/18**, suite **723**, mypy **112** files, ruff OK.
- Flight Recorder: `.workflow/TASK-032/`.

## 2026-06-15 — Phase 3 gate CLOSED (PASS-WITH-CONDITIONS)

- `.workflow/phase-3-gate-punchlist.md` — independent verification: pytest **705** passed, 1 deselected, 1 xfailed (REVIEW-004); mypy **112** files; ruff clean; harness **26/26**; `run_phase3_gate` **6/6**; `correlation_gate` **5/5**; tripwires **3/3** passing.
- DEC-053 ratified in `docs/decisions.md` (deferred directive persist refines DEC-028); `docs/plan.md:641` updated.
- README reconciled to Phase 3 complete state (705 tests, 32/35 tasks).
- TRACK into Sprint 4: static fault-flag guard (F-B), production-store table test (F-C), REVIEW-004 xfail, scope guard widen (F-H).

## 2026-06-15 — TASK-031 / DEC-052 citation-anchored host targeting

- Option A: `resolve_containment_target_from_citations` in `containment_policy.py`; gate uses validated citation IDs; `ambiguous_containment_target` fault flag wired (enum, outcome matrix, harness scenario, contracts §13).
- Orchestrator deferred persist uses gate directive target (not bundle re-scan).
- Phase 3 noisy gate GREEN: window filter (9999), honest noise bounds, citation-anchored host directive assertions.
- Tests: `tests/policy/test_citation_anchored_host_targeting.py` — **5**; phase3 gate **14** (+1 strict xfail); eval harness **25** scenarios.

## 2026-06-15 — TASK-031 gap #1 correction

- Binding discrimination is **window filter** (`excluded_record_ids: [9999]`); in-window cross-host noise **1004** bounded (not forbidden), aligned with TASK-030 `otrf_unrelated_in_window_noise`.
- Honest ceilings: `max_collected_facts: 5`, `max_noise_overcollection: 2`; gate GREEN on healthy tree.
- Forward pressure: `test_correlator_should_drop_cross_host_in_window_noise` strict xfail (REVIEW-004); host literals unchanged in `check_phase2_safety_on_noisy_bundle`.

## 2026-06-15 — TASK-031 gatekeeper hardening

- Binding correlation bounds: `noisy_correlated_real_telemetry.yaml` excludes **1004**/**9999**, `max_collected_facts: 4`, `max_noise_overcollection: 1`; gate surfaces correlator in-window over-collection (REVIEW-003).
- Host safety: literal `WORKSTATION1` / not `WORKSTATION2` assertions (non-tautological); multi-host resolver spec proposal in review (REVIEW-004).
- Tests: **13** phase3 gate tests incl. negative over-collection cases; `pytest tests/evals/` **82** passed; Phase 3 CLI exits non-zero until correlator discriminates.
- REQ-001 intake half: `evaluate_policy_gate` only (not TASK-028a `process_alert_intake`).

## 2026-06-15 — TASK-031 complete

- Phase 3 regression gate: `evals/run_phase3_gate.py` — required expected YAML, noisy correlation accuracy, identity compliance subprocess, account preflight prerequisite, Phase 2 safety on correlated bundle, optional Phase 2 harness.
- Expected scenario: `evals/correlation_expected/noisy_correlated_real_telemetry.yaml` (dual in-window noise bounded).
- Tests: `tests/evals/test_phase3_regression_gate.py` — **9**; CLI `python -m evals.run_phase3_gate` PASS.
- Verification: phase3 **9/9**, correlation **19/19** (5 CLI scenarios), suite **694**, mypy **112** files, ruff OK.
- Flight Recorder: `.workflow/TASK-031/`.

## 2026-06-15 — TASK-030 complete

- Correlation accuracy gate: `evals/correlation_gate.py` — manifest listing + checksum, corroboration contract, noise record attribution, ambiguity/window scenarios.
- Expected scenarios: four YAML files under `evals/correlation_expected/` (incl. unrelated in-window noise, window boundary).
- Tests: `tests/evals/test_correlation_gate.py` — **19**; CLI `python -m evals.correlation_gate` — 4/4 PASS.
- Verification: gate **19/19**, suite **685**, mypy **111** files, ruff OK.
- Flight Recorder: `.workflow/TASK-030/`.

## 2026-06-15 — TASK-029 reopen (gatekeeper)

- Removed `@pytest.mark.integration`; **12** compliance tests run in default suite.
- Negative cases through `evaluate_policy_gate`: two-sysmon / ambiguous-only → host `AUTO_CONTAIN` (not erroneous `ambiguous_target_identity` short-circuit).
- Added corroborated+`ambiguity_flag` case (spec.md:309 conjunction); account gate e2e on real correlated bundle.
- Verification: compliance **12/12**, suite **666**, mypy **110** files, ruff OK.

## 2026-06-15 — TASK-029 complete

- Identity compliance: `tests/correlation/test_correlator_identity_compliance.py` — initial 9 tests; orchestrator lazy-import cycle fix.
- Verification: integration **9/9**, suite **654** (10 deselected), mypy **110** files, ruff OK.
- Flight Recorder: `.workflow/TASK-029/`.

## 2026-06-15 — TASK-028a gatekeeper cleanup

- Repo hygiene: deleted stray `tmp-idem*.db` artifacts; `.gitignore` adds `tmp-*.db` (test DBs remain under pytest `tmp_path`).
- Deferred persist conflict: `DeferredDirectivePersistConflict` in `gate.py`; orchestrator catches in edict-append transaction, suppresses directive, rebuilds escalate edict with gate fault flag (`never_contain_live_conflict` / `revocation_feed_unhealthy` / `rate_limit_exceeded`).
- Test: `test_deferred_persist_never_contain_conflict_escalates_in_band` in `test_intake_stamp_actuation.py` (`InjectNeverContainOnStampBackend`).
- Metrics: post-actuation recording uses persisted edict + `directive_persisted` flag.
- Verification: suite **654**, eval **25/25**, mypy **110** files, ruff OK.

## 2026-06-15 — TASK-028a gatekeeper follow-up

- Stamp ordering: directive + edict in one transaction after terminal stamp only (`persist_directive=False` on intake gate eval); no orphaned directives on unknown/pending stamp.
- Eval harness: engine_intake directive DB assertions; runner expectation-key guard; `auto_contain_stamp_failed` scenario.
- Tests: `test_intake_stamp_actuation.py`, directive teeth + guard in `test_eval_harness.py`, unknown-stamp metrics assertion.
- Verification: suite **653**, eval **25/25**, mypy **110** files, ruff OK.

## 2026-06-15 — TASK-028a complete

- Production intake: `evaluate_policy_gate` + optional `MetricsCollector` on `process_alert_intake`; correlation bundle resolution (telemetry / override / skeleton default).
- Tripwires: `tests/engine/test_policygate_integration_tripwire.py` — **3** passing (xfail removed).
- Metrics: `tests/metrics/test_orchestrator_metrics.py` — **3**; suite **646**, eval harness **24/24**, mypy **110** files, ruff OK.
- Evals: `confirmed_malicious_sequence` + `never_contain_target` → `runner: engine_intake`.
- Flight Recorder: `.workflow/TASK-028a/`.

## 2026-06-15 — TASK-028 complete

- Correlation normalization: `src/praetor/correlation/` — Sysmon EventID 1, Security 4624, ±300s window, process GUID graph, Task 14 excerpt bridge.
- Fixtures: `tests/fixtures/sysmon/*`, `tests/fixtures/security/successful_logon_4624.json`; manifest checksums (4 entries).
- Tests: `tests/correlation/test_sysmon_normalization.py` — **9**; suite **638**, `mypy src evals consumer_sdk` OK (**110** files), ruff OK.
- Flight Recorder: `.workflow/TASK-028/`.

## 2026-06-13 — TASK-027 gatekeeper reopen

- Structural preconditions read from `request.payload["prompt_excerpt_set"]`; truncated adversarial fixture; structural `raw_source` key walk.
- Mocked Gemini tests: happy path, HTTPError, URLError, malformed response paths, prompt content.
- Mypy: `evals` added to packages; `types-PyYAML` dev dep; harness TypedDict fix; **102** files clean.
- Docs: `docs/decisions.md` DEC-047, `docs/eval_gates.md`.
- Tests: **14** deterministic adversarial + **1** deselected integration; eval suite **47**; full suite **629**.
- Note: `tests/evals/__init__.py` omitted (shadows top-level `evals` under pytest).

## 2026-06-13 — TASK-027 complete

- Real-provider adversarial excerpt probe: `evals/real_provider_adversarial.py` — instruction-like injection in normalized `command_line`, Task 14 structural pre-checks, optional `GeminiJudgmentProvider` (REST), log-only probabilistic integration test.
- Tests: `tests/evals/test_real_provider_adversarial.py` — **14** deterministic + **1** deselected integration; `pyproject.toml` markers + default exclusion + mypy `evals`.
- Verification: suite **629**, `mypy src evals consumer_sdk` OK (**102** files), ruff OK.
- Docs: `docs/eval_gates.md`, `docs/decisions.md` DEC-047.
- Flight Recorder: `.workflow/TASK-027/`.

## 2026-06-13 — TASK-026 matrix hardening follow-up

- `evals/outcome_matrix.py` — canonical SFE polarity keyed by `OutcomeMatrixFaultFlag`; matrix pair collectors.
- Harness: fail-closed `_assert_outcome` for escalate SFE; policy_gate kwargs (provider_health/latency/queue); policy preconditions (rate limit, breaker, ambiguity); failing stamp backend; idempotency repeat.
- Scenarios: +10 (`correlation_failure`, `invalid_model_citation`, `provider_health_breaker_open`, `latency_sla_exceeded`, `queue_aging_exceeded`, `policy_ambiguity`, `rate_limit_exceeded`, `containment_breaker_open`, `ticket_stamp_failed`, `policy_gate_idempotency`).
- Tests: `test_outcome_matrix_completeness_guard`, canonical enum + SFE polarity checks; **33** eval tests; suite **615**, `mypy src` OK, ruff OK.

## 2026-06-13 — TASK-026 complete

- Mandatory Phase 2 eval harness: `evals/harness.py` — scenario loader, runners (engine_intake, policy_gate, prompt_isolation, duplicate_retry, revocation_feed_degraded_mode), CLI `main()` with non-zero exit on failure.
- Scenarios: `evals/scenarios/*.yaml` — **14** mandatory fixtures; `evals/schemas/scenario_schema.json`.
- Tests: `tests/evals/test_eval_harness.py` — **19**; suite **601**, `mypy src` OK (96 files), ruff OK.
- Flight Recorder: `.workflow/TASK-026/`.

## 2026-06-13 — TASK-025 complete

- Analyst annotation storage: `src/praetor/annotations/store.py` — SQLite `analyst_annotations` table; `submit_annotation` with `authenticate_annotation_submission` + `verified_record_identity`; Pydantic cross-field validation; decision existence via `completed_decisions` or ledger edict; edict hash immutability.
- Tests: `tests/annotations/test_annotations.py` — **8**; suite **578**, `mypy src` OK (96 files), ruff OK.
- Flight Recorder: `.workflow/TASK-025/`.

## 2026-06-13 — TASK-024 gatekeeper follow-up

- Metrics contract hardened: policy-gate owns disposition recording; breaker true edge counters + recovery/current state; per-channel health delivery; §13 fault-flag enum; stamp terminal/non-terminal views; bounded feed-lag window (1000); edge cases for lag clamp, p99 small-n, threshold boundary (>=).
- Docs: `docs/contracts.md` §13 Metrics snapshot; DEC-045/046 in decisions.
- Tests: **27** metrics tests; suite **570**, `mypy src` OK (94 files), ruff OK.

## 2026-06-13 — TASK-024 complete

- Metrics collector: `src/praetor/metrics/{collector,events}.py` — in-process counters for dispositions, PolicyGate overrides, LLM fault flags, containment directives, queue aging, independent breaker/probe/production domains, stamp statuses, health-alert delivery, feed export lag (p99 + warning threshold), revocation feed unhealthy transitions.
- Tests: `tests/metrics/test_metrics.py` — **13**; suite **556**, `mypy src` OK (94 files), ruff OK.
- Flight Recorder: `.workflow/TASK-024/`.

## 2026-06-13 — TASK-023 gatekeeper follow-up

- Stamp failure contract: preserve `final_disposition` + existing fault flags; append `ticket_stamp_failed` (DEC-042).
- Redelivery while `PENDING_STAMP`: `ActiveAttemptExistsError` raised, not in-flight `IntakeResult` (DEC-043).
- Tests: +6 sequencing tests (fault-flag preservation, non-terminal raise, redelivery, ESCALATE recovery round-trip, payload fallback); **20** stamp sequencing; suite **543**.

## 2026-06-13 — TASK-023 complete

- Ticket stamp contract: `src/praetor/tickets/contract.py` — `StampContractDisposition`, `apply_terminal_stamp_to_disposition`, `stamp_status_allows_edict_append`.
- Intake: defer edict on in-flight stamp; apply terminal stamp disposition before ledger append.
- Recovery: delegate `_recovery_disposition_for_stamp` to shared contract.
- Tests: `tests/tickets/test_stamp_sequencing.py` — **14**; suite **537**, `mypy src` OK (91 files), ruff OK.

## 2026-06-13 — TASK-022 gatekeeper follow-up

- Removed unreachable intake-time queue-aging check; recovery remains production detector (DEC-040).
- DEC-039 extended: latency SLA spans full retry loop including backoff.
- Tests: slow AUTO_CONTAIN blocked by latency SLA; cumulative retry latency; queue boundary symmetry; PENDING_STAMP/STAMP_RESOLVED recovery scope; **14** engine latency+queue tests; suite **523**.

## 2026-06-13 — TASK-022 complete

- Latency SLA: `src/praetor/engine/timeouts.py` — monotonic-tracked provider calls; `latency_sla_exceeded` escalate with `system_fault_escalation=true` (DEC-039: v1 30s constant).
- Queue aging: `src/praetor/engine/queue_policy.py` — attempt age vs `max_queue_age_seconds`; intake + recovery emit `queue_aging_exceeded`.
- Orchestrator: queue check at ACTIVE; latency check after successful provider return; shared `_finish_system_fault`.
- Recovery: aged ALLOCATED/ACTIVE attempts emit escalate edict instead of silent abort.
- Tests: `tests/engine/test_latency_and_queue_aging.py` — **14**; suite **523**, `mypy src consumer_sdk` OK (92 files), ruff OK.

## 2026-06-12 — TASK-021 gatekeeper follow-up

- Expiry skew fail-closed (DEC-037): `clock > expires_at - skew`; fixes 20s-past-expiry actuation hole.
- Superseded-directive hole: live replacement supersedes verified directive → `lineage_conflict` (removed vacuous continue).
- Feed checksum: `FEED_CHECKSUM_MISMATCH` via `compute_feed_record_checksum`.
- Gap detection truncation-tolerant (DEC-038): contiguity for `seq <= cursor` only; read-ahead not a gap.
- Revocations in hand: all held records count regardless of cursor position.
- Tooling: `src/praetor/py.typed`, mypy `consumer_sdk`, hatchling force-include.
- Tests: consumer_sdk **24**; suite **509**, `mypy src consumer_sdk` OK (90 files), ruff OK.

## 2026-06-12 — TASK-021 complete

- Reference consumer verifier: `consumer_sdk/reference_verifier.py` — §10 pre-actuation checks 1–5 (clock sync, expiry, embedded hash, feed floor/staleness/gap, revocation, lineage conflict).
- Outcomes: `actionable`, `non_actionable` (expired/revoked), `escalate_human` (fail-closed).
- Tests: `tests/consumer_sdk/` — **13**; suite **498**, `mypy src` OK (88 files), ruff OK.

## 2026-06-11 — TASK-020 gatekeeper follow-up

- Manual revocation: `manual_revoke_directive_in_transaction` appends hash-chain ledger + marks directive revoked in same tx as feed + key clear (DEC-034); `write_manual_revocation_in_transaction` on StateStore.
- Builder: `require_critical_transaction`; caller `live_never_contain_entries` sole embed source; removed in-tx recompute fallback.
- Tests: mid-export feed floor, §9 hash negatives, non-empty embed round-trip, reason/count assertions, emergency fault-injection rollback.
- DEC-035: v1 emitted directives typically embed empty never-contain subset (exact-match relevance).
- Verification: containment **23** (lifecycle 15, revocation 8), suite **485**, `mypy src` OK (88 files), ruff OK.

## 2026-06-11 — TASK-020 complete

- Containment package: `src/praetor/containment/{lifecycle,revocation}.py` — proposed→emitted on persist, consumer embedded-hash verify, differentiated revocation triggers (manual, never-contain conflict, post-activation, supersession API).
- Refactored: `policy/gate.py`, `config/{activation,emergency}.py`, `engine/recovery.py`; thin re-exports in `policy/directive_builder.py` and `config/directives.py`.
- Scope guard: `containment` package allowed.
- Tests: `tests/containment/` — **16**; suite **478**, `mypy src` OK (88 files), ruff OK.
- Flight Recorder: `.workflow/TASK-020/`.

## 2026-06-11 — TASK-019 gatekeeper follow-up

- Probe-failure cooldown: `_record_probe_failure` sets `opened_at=now` (DEC-033); timer half-open reuse documented (DEC-032).
- Startup: `init_provider_health_breaker_schema` wired into `reconcile_policy_state` (step 6); `forbid_during_critical_transaction` guards schema init inside open tx.
- Race guards: `require_critical_transaction` on SOC-lead trigger and timer half-open entry.
- Tests: +10 (25 judgment provider-health tests); production-store and init-forbidden coverage.
- Verification: suite **462**, `mypy src` OK (85 files), ruff OK.

## 2026-06-11 — TASK-019 complete

- Provider-health breaker: `src/praetor/judgment/provider_health_breaker.py` — failure tripping, distinct health alert, half-open via SOC-lead or `window_seconds` timer, rate-limited canary probes, independent probe/production metrics.
- Canary payload: `PROVIDER_HEALTH_CANARY_PAYLOAD` on provider Protocol module.
- `provider_failure_trips_breaker()` includes `ProviderUnavailableError`; intake catch deferred (no Outcome Matrix row).
- Verification: judgment **15**, suite **452**, `mypy src` OK (85 files), ruff OK.
- Flight Recorder: `.workflow/TASK-019/`.

## 2026-06-09 — TASK-018 complete (+ gatekeeper follow-up)

- Rate limits: `src/praetor/policy/rate_limit.py` — sliding-window per-host/subnet/asset-group scopes; DEC-030 documents v1 `per_asset_group` = host asset_id.
- Containment breaker: window-elapse recovery on open-check (DEC-031); `_RateLimitRaceLoss` commits failure outside rolled-back emit tx.
- Health emit: `init_health_alert_emit_schema` at gate entry; race/ recovery/outbox tests exercise real paths.
- Verification: policy **43**, suite **437**, `mypy src` OK (84 files), ruff OK.
- Flight Recorder: `.workflow/TASK-018/`.

## 2026-06-08 — TASK-017 complete

- PolicyGate v1: `src/praetor/policy/gate.py` — deterministic gate with Outcome Matrix paths, single-transaction auto-contain emit, idempotency supersession, feed-health block.
- Containment policy: `src/praetor/policy/containment_policy.py` — host/account target resolution, snapshot/live never-contain, target-scoped policy ambiguity.
- Directive builder: `src/praetor/policy/directive_builder.py` — `ContainmentDirective` construction with embedded never-contain entries.
- Policy state: `src/praetor/policy/state.py` — rate counters, breaker rows, startup step 6 reconciliation.
- Production entrypoint: `src/praetor/runtime/startup.py` — `open_production_state_store` requires held singleton.
- Engine recovery: `run_engine_startup_recovery` now runs step 6 before step 7.
- Verification: policy **21**, suite **416**, `mypy src` OK (82 files), ruff OK.
- Flight Recorder: `.workflow/TASK-017/`.

## 2026-06-08 — TASK-016 complete

- Account identity and provenance: `src/praetor/evidence/provenance.py` — v1 Windows/Sysmon corroboration (`sysmon_event_log` + `windows_security_log`); same-provenance facts rejected.
- Policy identity: `src/praetor/policy/identity.py` — two-outcome evaluator: SID-backed + corroborated → `AUTO_CONTAIN` eligible; otherwise unconditional `escalate(ambiguous_target_identity)` per Outcome Matrix.
- Synthetic fixtures: `tests/fixtures/synthetic/*.json` drive corroboration tests before real correlation.
- Scope guard: `tests/contracts/test_scope_guard.py` now allows the intentional `policy` package.
- Verification: evidence corroboration **20**, suite **395**, `mypy src` OK (77 files), ruff OK.
- Flight Recorder: `.workflow/TASK-016/`.

## 2026-06-08 — TASK-015 complete

- Evidence citation validator: `src/praetor/evidence/citations.py` — validates cited evidence IDs and field paths against `EvidenceBundle`, requires citations for `escalate` / `auto_contain`, excludes `raw_source`, and returns resolved citation metadata including `ambiguity_flag`.
- Engine integration: walking-skeleton citation validation now delegates to the shared validator via `src/praetor/engine/citations.py`; `src/praetor/engine/skeleton.py` supplies the skeleton `EvidenceBundle`.
- Scope guard: `tests/contracts/test_scope_guard.py` now allows the intentional `evidence` package.
- Verification: evidence **7**, engine/provider citation regressions **15**, suite **366**, `mypy src` OK (74 files), ruff OK.
- Flight Recorder: `.workflow/TASK-015/`.

## 2026-06-08 — TASK-014 complete

- Prompt/excerpt hygiene: `src/praetor/judgment/excerpt.py` and `src/praetor/judgment/prompt.py` — sanitized `PromptExcerptSet`, 200-character head+tail truncation with exact omission markers, recursive `raw_source` exclusion, incomplete-content warning, and structured-output instructions.
- Engine provider request: `process_alert_intake` now passes provider payload with `prompt_excerpt_set`, `org_config_verbatim`, hashes, and instructions; `config_over_budget` remains pre-provider.
- Review hardening: added regressions for normalized/nested `raw_source` leaks and walking-skeleton `process_name` prompt availability.
- Verification: prompt **5**, judgment **15**, engine **26**, suite **359**, `mypy src` OK (72 files), ruff OK.
- Flight Recorder: `.workflow/TASK-014/`.

## 2026-06-08 — TASK-013 complete

- Judgment provider layer: `src/praetor/judgment/` — Protocol, request/probe types, typed provider failures, bounded timeout retry, scenario-scoped FakeProvider modes, and Vertex stub.
- Engine provider integration: `process_alert_intake` maps provider malformed JSON, timeout, and refusal to Outcome Matrix edicts; fabricated citation mode reaches existing citation validation.
- T2 prerequisite closed: `pending_stamp` recovery now has direct no-stamp-outbox-row coverage.
- Verification: judgment **10**, engine **26**, suite **354**, `mypy src` OK (70 files), ruff OK.
- Flight Recorder: `.workflow/TASK-013/`.

## 2026-06-04 — TASK-012 complete (Phase 1 gate)

- Walking skeleton: `src/praetor/engine/` — intake orchestrator, edict builder, citation check, startup recovery for attempts/directives.
- `open_state_store` runs engine recovery (step 7) before feed hook (step 8).
- Verification (re-run 2026-06-05): engine **25**, suite **341**, `mypy src` OK, ruff OK.
- Review hardening: single-site EMPTY_BUNDLE (DEC-006), crash-window/unknown-abort/failed-autocontain/correlation-redelivery tests, docstring step 4,5,7 (DEC-007).
- Flight Recorder: `.workflow/TASK-012/`.

## 2026-06-04 — TASK-011 complete

- Revocation feed package: outbox export metadata, JSONL exporter, startup recovery hook, PolicyGate age probe, unhealthy transition + health alert.
- Benchmark: `benchmarks/smoke_serialized_path.py` vs `provisional_alert_rate_targets`.
- Verification: revocation+runtime+benchmark **11**, suite **302**, `mypy src` OK (59 files).
- Flight Recorder: `.workflow/TASK-011/`.

## 2026-06-04 — TASK-010 complete

- TASK-010 (revised): contracts §7a pin, startup hook in `open_state_store`, 29 ledger tests, schema drift check, audit/deletion/error-normalization coverage.

## 2026-06-03 — TASK-009 complete

- Org config package, example YAML, contracts §3a pins, cross-cutting store/hashing/contracts wiring.
- Verification: config **55**, suite **254**, `mypy src` OK, VERIFY-004/004b ruff OK.
- Flight Recorder: `.workflow/TASK-009/` closed.

## 2026-06-03 — TASK-009 third reopen (verification green, not closed)

- Local gaps: strict policy integers, `PreflightError` on binding serialize failures, fetch verifies JSON `snapshot_hash`, multi-verbatim per binding hash, stable health pending ids + activation/emergency drain.
- Tests: `tests/config/` — **55**; full `pytest -q` → **254**; `mypy src` OK; scoped TASK-009 `ruff` OK.
- `docs/contracts.md` §3a updated (hash vector, verbatim render rows, fetch integrity).
- Deferred: ledger chain (Task 10), intake `config_over_budget` gate (Task 12), repo-wide ruff E501.

## 2026-06-03 — TASK-009 reopen (gate review) — superseded

- Earlier pass claimed 29/228; superseded by third reopen evidence above.

## 2026-06-03 — TASK-009 complete (superseded by reopen)

- **`src/praetor/config/`:** loader, preflight, snapshot hash, activation with post-activation reconciliation, emergency never-contain, SQLite state for active config / emergencies / outstanding directives.
- **`configs/example_org.yaml`:** valid reference config.
- **`StateStore.write_automated_revocation_in_transaction`:** avoids nested `critical_transaction` during activation/emergency scans.
- Tests: `tests/config/` — **22** tests.
- Verification: `pytest -q` → 218 passed; `mypy src` → 47 files pass.
- Flight Recorder: `.workflow/TASK-009/`.
- Gap: ledger hash-chain append (Task 10); provisional hard character budget constant; intake `config_over_budget` gate (Task 12).

## 2026-06-01 — TASK-008 verification hardening (reopen)

- **G-1 fixed:** `FailingJsonlSink` moved to `tests/alerts/_fakes.py`; removed from production API.
- **G-2 fixed:** `SystemHealthAlert` docstring corrected — contract is payload; delivery in SQLite (DEC-026).
- **G-3 fixed:** `_deliver_to_sink` catches all `Exception`; records `exception_type`.
- **G-4–G-13 fixed:** 14 new tests — record guards, FK regression, nested critical tx, duplicate alert_id, fail→fail, at-least-once JSONL, retry query, import smoke, non-OSError sink.
- **G-14 documented:** `_initialized_conn_ids` v1 single-connection lifetime comment.
- Tests: `tests/alerts/test_system_health_outbox.py` — **23** tests.
- Verification: `pytest -q` → 196 passed; `mypy src` → 37 files pass; `ruff check` pass.

## 2026-06-01 — TASK-008 complete

- **`src/praetor/alerts/`:** `outbox.py`, `system_health.py` — durable SQLite health alert outbox; per-channel delivery tracking (`jsonl`, `stdout`); persist-before-deliver; retry failed channels; future channels via delivery table rows.
- Tests: `tests/alerts/test_system_health_outbox.py` — **9** tests.
- Verification: `pytest -q` → 182 passed; `mypy src` → 37 files pass.
- Flight Recorder: `.workflow/TASK-008/`.
- Gap: startup delivery worker (Task 11–12); emitter wiring (Task 9+).

## 2026-06-01 — TASK-007 verification hardening (reopen)

- **G-1 fixed:** `ConnectionError`/transport ambiguity → durable `unknown` via `_is_backend_ambiguity`; programmer `ValueError` not swallowed.
- **G-2–G-9 fixed:** 10 new tests — pending restart recovery, EMPTY_BUNDLE path, cached failed terminal, payload authority, DEC-022 additive schema, idempotent recovery path, `record_stamp_outcome` PENDING guard, `processing_attempt_identity` semantics (DEC-023).
- **G-10 deferred:** outbox timestamps use `isoformat()` (+00:00); Task 23 hazard if copied into hashed edict fields.
- **G-11 documented:** per-conn schema cache validates table exists (recycled `id(conn)` safety).
- Tests: `tests/tickets/test_stamp_outbox.py` — **21** tests.
- Verification: `pytest -q` → 173 passed; `mypy src` → 34 files pass.

## 2026-06-01 — TASK-007 complete

- **`src/praetor/tickets/`:** `outbox.py`, `stamp.py` — durable SQLite stamp outbox keyed by `stamp_id`; pending before external call; `succeeded`/`failed`/`unknown` outcomes; recovery retry with same `stamp_id`.
- Tests: `tests/tickets/test_stamp_outbox.py` — 11 tests.
- Verification: `pytest -q` → 163 passed; `mypy src` → 34 files pass.
- Flight Recorder: `.workflow/TASK-007/`.
- Gap: attempt FSM / edict append wiring (Task 23); startup recovery enumeration (Task 11–12).

## 2026-06-01 — TASK-006 verification fix pass

- Added 20 tests: feed sequence reopen/rollback, manual revocation rollback, completed-edict conflict, FSM negatives, idempotency duplicate, schema version reject, abort same-input retry, singleton contract.
- Implementation: `IncompatibleSchemaError`, `IdempotencyKeyConflictError`, `verify_schema_version`, `read_feed_sequence_next`.
- Verification: `pytest -q` → 152 passed; Task 6 file → **32** tests collected; `mypy src` pass.
- Artifacts corrected (V-002 wording, test count).

## 2026-06-01 — TASK-006 complete

- **`src/praetor/state/`:** `store.py`, `attempts.py`, `completed_decisions.py`, `idempotency.py` — attempt FSM, three-tuple dedup, manual/automated revocation + feed outbox sequence.
- Tests: `tests/state/test_attempt_lifecycle.py` — 32 tests (after fix pass).
- Verification: `pytest -q` → 152 passed; `mypy src` → 31 files pass.
- Flight Recorder: `.workflow/TASK-006/`.
- Gap: ledger chain append (Task 10); feed export (Task 11); enumeration helpers (11/12).

## 2026-06-01 — TASK-005 reopen complete

- **DEC-017:** `init_state_dir` one-shot WAL bootstrap; guard verify-only.
- **DEC-018:** nested `critical_transaction` forbidden (per-connection sentinel).
- **DEC-019:** Windows `msvcrt.locking` ratified vs spec `CreateFile` wording.
- **`verify_synchronous`:** `REQUIRED_SYNCHRONOUS_MIN=1` (NORMAL).
- Tests: 28 startup guard + bare-BEGIN scope guard; 119 total `pytest`.
- Verification: `mypy src` → 27 files pass.
- Gap: process-exit wrapper deferred to Task 12.

## 2026-06-01 — TASK-005 complete

- **`src/praetor/runtime/singleton.py`:** OS-level singleton file lock (`flock` on POSIX, `msvcrt.locking` on Windows); held for process lifetime; non-zero exit code on contention.
- **`src/praetor/state/sqlite_guard.py`:** WAL journal mode verification, explicit `isolation_level=None`, `critical_transaction` with `BEGIN IMMEDIATE`, `run_startup_sqlite_guard` entry point.
- Tests: `tests/runtime/test_startup_guard.py` — 13 tests including subprocess second-process block.
- Verification: `pytest -q` → 107 passed; `mypy src/praetor/runtime src/praetor/state`; `ruff check` on new modules.
- Flight Recorder: `.workflow/TASK-005/`.
- Gap: full SQLite PRAGMA list deferred to absent `docs/operator_runbook.md` (Task 35).

## 2026-06-01 — TASK-004 complete

- **`src/praetor/auth/`:** `Principal`, role literals, `TokenVerifier`, three external surfaces, `verified_record_identity` (rejects self-asserted overrides), `guard_internal_only` + `authenticate_external_write` for internal-op enforcement.
- Tests: `tests/auth/test_auth_primitives.py` — 28 tests.
- Tooling: mypy/ruff added to dev deps; auth module passes strict mypy and ruff.
- Verification: `pytest -q` → 90 passed; `mypy src/praetor/auth`; `ruff check src/praetor/auth tests/auth`.
- Flight Recorder: `.workflow/TASK-004/`.

## 2026-06-01 — TASK-003 complete (doc-first correction)

- **`docs/contracts.md`:** added §5 `stamp_id` (four-part delimited hash over completed-edict three-tuple; stable across attempts for outbox recovery idempotency); ratified §7 `EMPTY_BUNDLE` preimage `praetor:v1:empty_bundle`; renumbered §6–§15.
- **`src/praetor/hashing/`:** canonical serialization; `derive_decision_id`, `derive_idempotency_key`, `derive_stamp_id` (three-tuple only), feed checksum, never-contain hash.
- Tests: `tests/hashing/test_canonical.py` — includes stamp stability across attempts; scope guard allows `docs/contracts.md` only.
- Verification: `pytest -q` → 62 passed.
- Flight Recorder: `.workflow/TASK-003/`.

## 2026-06-01 — TASK-002 complete

- Implemented 14 versioned Pydantic v2 contracts under `src/praetor/contracts/` with `extra=forbid`, Literal `schema_version` / `record_type`, and §10–§11 validators.
- Generated deterministic JSON Schema artifacts in `schemas/` (not authoritative).
- Tests: `tests/contracts/` — round-trip, negative validation, export stability, scope guard.
- Verification: `pytest -q` → 36 passed; `python -m praetor.contracts.schema_export`.
- Flight Recorder: `.workflow/task-002/`.

## 2026-05-31 — TASK-001 complete

- Implemented repo skeleton: `pyproject.toml` (hatchling, `requires-python >=3.11`), `src/praetor/`, smoke tests, fixture manifest stub.
- Verification: `pip install -e ".[dev]"`, `pytest -q` → 2 passed.
- Flight Recorder: `.workflow/task-001/` (plan, verification, review, final-report).

## 2026-05-31 — Memory Bank initialized

- Read authoritative planning docs: `docs/prd.md`, `docs/spec.md`, `docs/plan.md`, `docs/contracts.md`.
- Populated Memory Bank to summarize and index docs for agent operations.

## Project state

| Area | State |
|------|--------|
| Product definition | Complete in `docs/` |
| V1 implementation plan | Complete — 35 tasks in `docs/plan.md` |
| V2 implementation plan | Initialized — 36 tasks in `docs/proposals/v2_implementation_plan.md`; Memory Bank indexed; **0/36** started |
| Package / tests | Task 1 done — `pytest` runs, `praetor` imports |
| Contracts | Task 2 done — `src/praetor/contracts/`, `schemas/` |
| Hashing | Task 3 done — `src/praetor/hashing/` + `docs/contracts.md` §1–§9 |
| Auth | Task 4 done — `src/praetor/auth/` |
| Runtime / startup guard | Task 5 done — `src/praetor/runtime/`, `src/praetor/state/sqlite_guard.py` |
| State store / lifecycle | Task 6 done — `src/praetor/state/{store,attempts,completed_decisions,idempotency}.py` |
| Ticket stamp outbox | Task 7 done — `src/praetor/tickets/{outbox,stamp}.py` |
| SystemHealthAlert outbox | Task 8 done — `src/praetor/alerts/{outbox,system_health}.py` |
| Org config | Task 9 done — `src/praetor/config/` |
| Ledger hash chain | Task 10 done — `src/praetor/ledger/` |
| Revocation feed export | Task 11 done — `src/praetor/revocation/` |
| Walking skeleton / recovery | Task 12 done — `src/praetor/engine/` (**Phase 1 complete**) |
| CI / eval harness | Task 26–27 done — mandatory harness + probabilistic real-provider probe |
| Operator runbooks | Task 35 done — `docs/operator_runbook.md`, `docs/architecture.md` |

## Next recommended steps

1. **V2-001** — Authorization posture decision (`docs/decisions.md`, `docs/proposals/v2_hardening.md`).
2. **V2-002** – **V2-004** — parallel decision/contract tasks (no cross-deps within Gate 0).
3. Close **V2 Gate 0** before V2-005 (strict containment schema).
