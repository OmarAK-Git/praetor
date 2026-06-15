# DOCUMENT 2 - Praetor Implementation Plan

## Build Order

Durable core first: contracts, canonical hashing, startup guards, lifecycle/outboxes, config, ledger, revocation feed, walking skeleton, and smoke benchmark. Then judgment, prompt construction, PolicyGate, breakers/probes, directive lifecycle, reference consumer verifier, metrics, evals, and adversarial probe. Then correlation and identity compliance. Then detection portability and Splunk demo. Then codification, production benchmarks, and runbooks.

## Sprint Groupings

- Sprint 1: Tasks 1-12. Contracts, canonical serialization, auth, startup guards, SQLite lifecycle/outboxes, config, ledger, revocation feed, walking skeleton, provisional alert-rate targets, smoke benchmark, and Phase 1 gate recovery.
- Sprint 2: Tasks 13-27. Judgment, prompt construction, PolicyGate, breakers, half-open probes, directive lifecycle, consumer verifier, metrics, annotations, Phase 2 eval harness, real-provider adversarial probe.
- Sprint 3: Tasks 28-31, plus 28a. Correlation normalization (28), production orchestrator PolicyGate and metrics integration (28a, depends on 28), identity compliance (29), accuracy gate (30), Phase 3 harness (31).
- Sprint 4: Tasks 32-33. Detection portability and Splunk demo.
- Sprint 5: Tasks 34-35. Codification, production throughput benchmark, operator runbooks.

## Task 1 - Repository Structure and Test Harness
Complexity: S | Depends on: none

Test first: smoke import passes; fixture manifest loads.

Files: `pyproject.toml`, `src/praetor/__init__.py`, `tests/test_smoke.py`, `tests/fixtures/README.md`, `tests/fixtures/fixture_manifest.yaml`.

Done when: `pytest` runs, package imports, fixture manifest stub exists.

## Task 2 - Versioned Contract Models
Complexity: L | Depends on: Task 1

Test first:

- All models round-trip serialization.
- `pass` rejected as Disposition enum value.
- `AnalystAnnotation` cross-field validation enforced in both directions.
- `DecisionEdict` has `system_fault_escalation` boolean and `record_type=decision_edict`.
- `ContainmentDirective` has `status`, `live_never_contain_hash`, embedded target-relevant never-contain entries, `minimum_feed_sequence_at_issue`, and hard maximum lifetime validation of 300 seconds.
- `ContainmentDirective` does not include `revocation_feed_id`; schema comment reserves that field for post-v1.
- `NeverContainSnapshotRecord` has required fields and `record_type=never_contain_snapshot`.
- `EmergencyNeverContainRecord` has required fields, `record_type=emergency_never_contain`, and hard maximum lifetime validation of 48 hours.
- `DirectiveRevocationRecord` has `record_type=directive_revocation`, `reason_code`, `ledger_commit_at`, `idempotency_key_cleared`, and requires `superseded_by_directive_id` when `reason=supersession`.
- `RevocationFeedRecord` has `schema_version`, `sequence_number`, `directive_id`, `revocation_id`, `reason_code`, `revoked_at`, `ledger_commit_at`, and `record_checksum`.
- `SystemHealthAlert` and `CanonicalAccountIdentity` round-trip and export JSON Schema.
- JSON Schema export includes `schema_version` in all models.

Files: `src/praetor/contracts/*.py`, `tests/contracts/test_contract_roundtrip.py`, `schemas/`.

Done when: all versioned contracts present with schemas; all four ledger record types have distinct `record_type` values; feed and directive lifetime constraints are schema-tested.

## Task 3 - Canonical Serialization and Hash Constants
Complexity: M | Depends on: Task 2

Test first:

- Identical input produces stable hash across calls.
- `NaN`/`Infinity` raises `CanonicalSerializationError`.
- Datetimes serialized as UTC RFC3339 with exactly six fractional digits.
- Object keys sorted lexicographically by Unicode code point.
- Unknown fields raise error.
- `EMPTY_BUNDLE` sentinel hashes deterministically.
- `decision_id`, idempotency key, and `stamp_id` use distinct domain constants with length-delimited input ordering.
- Revocation-feed `record_checksum` formula is defined and tested as corruption detection only.
- No computation site uses inline domain strings; all reference module-level constants.

Files: `src/praetor/hashing/canonical.py`, `src/praetor/hashing/domains.py`, `docs/contracts.md`, `tests/hashing/test_canonical.py`.

Done when: `docs/contracts.md` is the single source of truth for domain constants, input orderings, embedded never-contain verification, feed checksum, feed sequence semantics, and consumer pre-actuation checks.

## Task 4 - Authenticated Write Surface Primitives
Complexity: M | Depends on: Task 2

Test first:

- `soc_lead` token accepted for org-config activation and emergency never-contain; wrong role rejected.
- `analyst` token accepted for annotation; wrong role rejected.
- Missing token rejected on all three surfaces.
- Verified principal identity extracted and available for records.
- Ledger append, directive emission, and feed export are not externally callable.

Files: `src/praetor/auth/principal.py`, `src/praetor/auth/verifier.py`, `tests/auth/test_auth_primitives.py`.

Done when: three role-tagged external surfaces exist; token issuance is documented out of scope.

## Task 5 - SQLite Startup Guard and Process Singleton
Complexity: M | Depends on: Task 1

Test first:

- Startup fails if singleton file lock cannot be acquired.
- Startup fails if SQLite journal mode is not WAL.
- Startup fails if connection isolation is not explicit or `BEGIN IMMEDIATE` is not enforced on critical paths.
- Lock is held through process lifetime.

Files: `src/praetor/runtime/singleton.py`, `src/praetor/state/sqlite_guard.py`, `tests/runtime/test_startup_guard.py`.

Done when: a second Praetor process cannot start against the same state directory; WAL misconfiguration exits non-zero.

## Task 6 - SQLite State Store and Attempt Lifecycle
Complexity: L | Depends on: Tasks 2, 3, 5

Test first:

- At most one non-terminal attempt per `alert_id`.
- Duplicate intake loser re-checks completed edict after acquiring lock.
- Completed-edict uniqueness enforced on alert/bundle/config three-tuple.
- Attempt states transition correctly.
- Aborted attempts do not block future changed-input attempts.
- SOC-lead manual revocation writes `DirectiveRevocationRecord`, feed outbox row, and clears idempotency key in one transaction.
- Automated revocation writes `DirectiveRevocationRecord` and feed outbox row without clearing key.

Files: `src/praetor/state/store.py`, `src/praetor/state/attempts.py`, `src/praetor/state/completed_decisions.py`, `src/praetor/state/idempotency.py`, `tests/state/test_attempt_lifecycle.py`.

Done when: durable lifecycle is authoritative for per-alert side effects; single-writer deployment constraint documented.

## Task 7 - Ticket Stamp Outbox
Complexity: L | Depends on: Tasks 3, 6

Test first:

- Pending outbox entry written before external call.
- Definite success/failure recorded durably.
- Timeout records `unknown`.
- Recovery retry uses same `stamp_id`.
- Duplicate `stamp_id` is idempotent in fake ticket backend.
- Non-idempotent backend residual double-stamp risk documented.

Files: `src/praetor/tickets/outbox.py`, `src/praetor/tickets/stamp.py`, `tests/tickets/test_stamp_outbox.py`.

Done when: stamp outcome is durable and `unknown` is distinguishable from `failed`.

## Task 8 - SystemHealthAlert Outbox
Complexity: M | Depends on: Tasks 2, 6

Test first:

- Health alerts persisted before delivery attempt.
- JSONL and stdout delivery statuses recorded per entry.
- Failed delivery remains retryable.
- Outbox schema supports future delivery channels without migration.
- `revocation_feed_unhealthy` health alert is supported.

Files: `src/praetor/alerts/system_health.py`, `src/praetor/alerts/outbox.py`, `tests/alerts/test_system_health_outbox.py`.

Done when: critical safety alerts have durable delivery tracking; `SystemHealthAlert` records are confirmed outbox-only.

## Task 9 - Org Config Loader, Preflight, Snapshot Binding, and Emergency Never-Contain
Complexity: L | Depends on: Tasks 2, 3, 4, 6, 8

Test first:

- Valid config loads; snapshot hash is stable.
- Missing required section fails preflight.
- Config over hard budget fails with `config_over_budget`.
- Containment policy conflicts without precedence fail preflight.
- Provider-health breaker missing `probe_rate_limit_per_minute` fails.
- Circuit-breaker sections missing base fields fail.
- Asset registry entry missing `subnet_membership` fails.
- Directive lifetime over 300 seconds fails.
- Emergency never-contain lifetime over 48 hours fails.
- Revocation-feed propagation delay defaults to 60 seconds and must be below directive max lifetime.
- Consumer clock skew defaults to 30 seconds.
- `account_auto_contain_enabled` defaults false.
- Provisional sustained and burst alert-rate targets are present before Sprint 1 ends.
- In-flight alert keeps original snapshot after config edit.
- Post-activation reconciliation revokes outstanding unexpired directives matching new never-contain list and emits health alerts.
- Emergency never-contain writes EmergencyNeverContainRecord, emits health alert, expires correctly, participates in live check under the same serializable lock, and cannot authorize containment.
Adding an emergency entry synchronously scans already-committed outstanding unexpired directives for the target and writes one never_contain_conflict DirectiveRevocationRecord plus feed outbox row per match, in the same transaction, without clearing idempotency keys; the conflict SystemHealthAlert is enqueued in the same transaction and flushed after commit.
A directive committed before the emergency-entry transaction is revoked by the scan; a directive whose live-check lock predates the commit is not caught (race case, covered by expiry and consumer feed check).

Files: `src/praetor/config/loader.py`, `src/praetor/config/snapshot.py`, `src/praetor/config/preflight.py`, `src/praetor/config/activation.py`, `src/praetor/config/emergency.py`, `configs/example_org.yaml`, `tests/config/test_org_config_loader.py`, `tests/config/test_config_activation.py`, `tests/config/test_emergency_never_contain.py`.

Done when: config preflight validates new lifetime, feed, clock, feature-gate, and throughput-target requirements.

## Task 10 - Hash-Chained Audit Log and Snapshot Records
Complexity: L | Depends on: Tasks 2, 3, 5, 6, 8

Test first:

- First record has `ledger_previous_hash=null`.
- Subsequent records chain correctly.
- Tampering with any prior record detected.
- Interleaved `DecisionEdict`, `DirectiveRevocationRecord`, `NeverContainSnapshotRecord`, and `EmergencyNeverContainRecord` verify regardless of record type.
- Unrecognized `record_type` is chain integrity violation.
- Startup with tampered chain emits health alert and refuses to start.
- Append is one serializable SQLite transaction.
- `NeverContainSnapshotRecord.snapshot_content` covers permanent and active emergency entries.

Files: `src/praetor/ledger/hash_chain.py`, `src/praetor/ledger/store.py`, `src/praetor/ledger/startup.py`, `tests/ledger/test_hash_chain.py`, `tests/ledger/test_startup_verification.py`.

Done when: all four record types share one tamper-evident chain and startup tamper detection refuses intake.

## Task 11 - Revocation Feed Outbox, Exporter, Startup Recovery, and Smoke Benchmark
Complexity: L | Depends on: Tasks 6, 8, 10

Test first:

- Revocation transaction assigns gap-free `sequence_number` and inserts feed outbox row atomically with `DirectiveRevocationRecord`.
- JSONL exporter writes rows sequentially in sequence order.
- `record_checksum` verifies after write.
- Export retry uses configured `max_feed_export_retries`.
- Retry exhaustion transitions to `revocation_feed_unhealthy` and emits health alert.
- Oldest pending row age from `ledger_commit_at` is exposed for PolicyGate.
- Startup recovers pending feed rows before enabling auto-contain.
- Startup enters degraded non-actuating mode if feed recovery cannot meet SLO.
- Append-only JSONL has no rotation machinery.
- Smoke benchmark measures serialized transaction path against provisional sustained/burst targets.

Files: `src/praetor/revocation/feed.py`, `src/praetor/revocation/exporter.py`, `src/praetor/revocation/outbox.py`, `benchmarks/smoke_serialized_path.py`, `tests/revocation/test_feed_exporter.py`, `tests/runtime/test_feed_startup_recovery.py`, `tests/benchmarks/test_smoke_benchmark.py`.

Done when: consumers have a sequential feed projection and Praetor can detect/block auto-containment when feed delivery is unhealthy.

## Task 12 - Walking Skeleton Decision Flow and Recovery
Complexity: L | Depends on: Tasks 6-11

Test first:

- Hardcoded bundle + hardcoded valid judgment produces one valid `DecisionEdict`.
- Correlation failure produces `escalate(correlation_failure)`, attempt aborted, `EMPTY_BUNDLE` in `decision_id`.
- Config over budget produces `escalate(config_over_budget)` with no LLM call.
- Invalid citation produces `escalate(invalid_model_citation)`.
- Crash at each lifecycle state reconciles before intake; no recovery path emits containment.
- Startup scans outstanding unexpired directives against current never-contain and writes revocations/feed rows for matches.
- Crash during emergency record write leaves record fully committed or absent.
- Ticket stamp payload present in edict.

Files: `src/praetor/engine/orchestrator.py`, `src/praetor/engine/ids.py`, `src/praetor/engine/recovery.py`, `tests/engine/test_walking_skeleton.py`, `tests/engine/test_crash_recovery.py`.

Done when: startup recovery closes audit and feed gaps without unsafe side effects.

## Task 13 - Provider Abstraction and FakeProvider Injection Modes
Complexity: M | Depends on: Task 12

Test first:

- FakeProvider valid, malformed JSON, timeout, refusal, and fabricated citation modes work per scenario.
- Provider timeout triggers bounded retry then `provider_timeout`.
- FakeProvider implements `probe(canary_payload)`.
- Vertex provider stub implements Protocol.
- Bounded retries with backoff implemented.

Files: `src/praetor/judgment/provider.py`, `src/praetor/judgment/fake_provider.py`, `src/praetor/judgment/vertex_provider.py`, `tests/judgment/test_provider_failures.py`.

Done when: engine depends on Protocol and failure modes are scenario-scoped.

## Task 14 - Prompt Construction and Excerpt Hygiene
Complexity: L | Depends on: Tasks 9, 13

Test first:

- Every prompt fact has stable evidence ID.
- Excerpts are at most 200 Unicode characters.
- Truncation uses `[...omitting N characters]`.
- High-risk unbounded fields use head+tail truncation.
- Model is told when excerpt content is incomplete.
- `raw_source` absent from all prompt output.
- Full org config rendered verbatim; character budget enforced first.
- Structured-output schema instructions present.

Files: `src/praetor/judgment/prompt.py`, `src/praetor/judgment/excerpt.py`, `tests/judgment/test_prompt_isolation.py`.

Done when: `PromptExcerptSet` is the sole provider-facing evidence content.

## Task 15 - Evidence Citation Validator
Complexity: M | Depends on: Task 2

Test first:

- Valid evidence IDs and field paths pass; invalid refs fail.
- Missing citations fail for `escalate` and `auto_contain` proposals.
- `ambiguity_flag` on cited fact is accessible for identity decisions.

Files: `src/praetor/evidence/citations.py`, `tests/evidence/test_citation_validation.py`.

Done when: one shared validator covers rationale validation and PolicyGate citation checks.

## Task 16 - Canonical Account Identity and Synthetic Provenance Tests
Complexity: M | Depends on: Tasks 2, 15

Test first:

- Facts missing `provenance_path` fail schema validation.
- `CanonicalAccountIdentity` requires SID, domain, account name, account type, authority source, and ambiguity flag.
- SID-absent identity cannot authorize account containment.
- Same-provenance facts do not corroborate account containment.
- One `sysmon_event_log` plus one `windows_security_log` satisfies corroboration.
- Ambiguous target with insufficient corroboration produces `escalate(ambiguous_target_identity)`.

Files: `src/praetor/evidence/provenance.py`, `src/praetor/policy/identity.py`, `tests/evidence/test_account_corroboration.py`, `tests/fixtures/synthetic/*.json`.

Done when: account containment eligibility is testable before real correlation exists.

## Task 17 - Deterministic PolicyGate v1
Complexity: L | Depends on: Tasks 9, 11, 12, 14-16

**Blocking Phase 1 gate prerequisites (must land before this task starts):**

- Startup recovery step 6 — idempotency-key, rate-counter, and breaker reconciliation in `src/praetor/engine/recovery.py` (currently absent and documented as such at the `run_engine_startup_recovery` docstring). PolicyGate introduces the rate-limit / breaker / idempotency state this step is meant to reconcile across a crash; without it, recovery cannot restore that state safely.
- Production startup must pass a held `SingletonLock` to `open_state_store(..., singleton=...)`, and a test must assert the lockless open path is rejected for the production entrypoint. The fail-closed guard path exists (Task 5 / `run_startup_sqlite_guard`) but is not yet forced on callers.

Test first:

- Invalid evidence citation produces `escalate(invalid_model_citation)`.
- Snapshot never-contain match produces `escalate(never_contain_snapshot)`.
- Live permanent or emergency never-contain match produces `escalate(never_contain_live_conflict)`.
- Active emergency entry appears in embedded entries when evaluated.
- Insufficient account corroboration produces `escalate(ambiguous_target_identity)`.
- Valid account identity still produces `escalate(account_containment_disabled)` when feature gate is false.
- Account auto-contain can pass only when feature gate is true and identity checks pass.
- Target-scoped policy conflict produces `escalate(policy_ambiguity)`.
- Rate limit exceeded produces `escalate(rate_limit_exceeded)`.
- Duplicate idempotency key suppresses new emission.
- Expired directive idempotency key allows fresh re-issue (same key, no supersession reference, no revocation record).
- Feed unhealthy or oldest pending row past SLO produces `escalate(revocation_feed_unhealthy)`.
- Live never-contain, feed health, idempotency, and rate-limit updates occur in one serializable transaction.
- `proposed_disposition` and `final_disposition` separately recorded.
- Full Outcome Matrix enforced.

Files: `src/praetor/policy/gate.py`, `src/praetor/policy/containment_policy.py`, `src/praetor/policy/directive_builder.py`, `src/praetor/policy/identity.py`, `tests/policy/test_policy_gate.py`, `tests/policy/test_containment_policy.py`.

Done when: `auto_contain` is impossible without all deterministic checks, including feed health and account feature gate.

## Task 18 - Transactional Rate Limits and Containment Breaker
Complexity: L | Depends on: Tasks 6, 17

Test first:

- Per-host, per-subnet, and per-asset-group limits block excess containment.
- Unregistered target contributes to `per_host` only.
- Concurrent attempts serialized.
- Sliding-window failures trip containment breaker.
- Breaker trip emits health alert.
- Rate-limit counters persist unchanged through tripped period.
- `success_reset_threshold` successes required for reset.

Files: `src/praetor/policy/rate_limit.py`, `src/praetor/policy/circuit_breaker.py`, `tests/policy/test_rate_limits.py`, `tests/policy/test_containment_circuit_breaker.py`.

Done when: breaker and limits cannot be bypassed by races.

## Task 19 - Provider-Health Breaker with Half-Open Probes
Complexity: L | Depends on: Tasks 8, 13, 18

Test first:

- Provider failures trip provider-health breaker.
- Production alerts escalate while open.
- Breaker trip emits distinct health alert.
- SOC-lead trigger and configured timer enter half-open probe mode.
- Probe calls use synthetic canary payload and no real alert data.
- Probe calls rate-limited by `probe_rate_limit_per_minute`.
- Probe metrics independent from production metrics.
- Probe failure resets countdown and reopens breaker.
- Consecutive probe successes close breaker.
- Provider and containment breaker states independent.

Files: `src/praetor/judgment/provider_health_breaker.py`, `tests/judgment/test_provider_health_breaker.py`.

Done when: provider recovery is possible without production-alert test traffic.

## Task 20 - Directive Lifecycle and Revocation
Complexity: L | Depends on: Tasks 10, 11, 17, 18

Test first:

- `ContainmentDirective.status` transitions from `proposed` to `emitted`.
- Directive expiry cannot exceed 300 seconds.
- Account directive `target_id` is SID, not name.
- Directive embeds target-relevant never-contain entries and `live_never_contain_hash`.
- `minimum_feed_sequence_at_issue` equals the highest feed sequence whose export was verified complete before issuance, never a sequence that is only assigned but not yet confirmed exported; a directive issued while another revocation is mid-export uses the last verified-exported sequence, so a fresh consumer cursor is never rejected against a floor Praetor had not yet published.
- Consumer can verify embedded entries hash.
- Revocation triggers write ledger record and feed outbox row.
- Post-emission conflict: health alert emitted; idempotency key not cleared.
- Manual revocation: record, feed row, and key clear in one transaction.
- Supersession: record includes `superseded_by_directive_id`; key not cleared.
- Post-activation reconciliation creates revocation record, feed row, and health alert.

Files: `src/praetor/containment/lifecycle.py`, `src/praetor/containment/revocation.py`, `tests/containment/test_directive_lifecycle.py`, `tests/containment/test_revocation.py`.

Done when: all revocation triggers are differentiated and feed projection is created for each.

## Task 21 - Reference Consumer Verifier
Complexity: M | Depends on: Tasks 3, 11, 20

Test first:

- Expired directive returns non-actionable with structured reason.
- Revoked directive returns non-actionable.
- Embedded never-contain hash mismatch returns escalate-human.
- Feed cursor below `minimum_feed_sequence_at_issue` returns escalate-human.
- Feed stale beyond propagation delay plus clock skew returns escalate-human.
- Sequence gap returns escalate-human.
- Clock-sync uncertainty beyond configured skew returns escalate-human.
- Overlapping target/scope lineage conflict returns escalate-human.
- Valid directive with fresh feed and no revocation returns actionable.
- Return object includes `directive_id`, `target`, `failed_check`, `last_seen_sequence`, `consumer_clock_at_check`, and `expires_at`.

Files: `consumer_sdk/reference_verifier.py`, `tests/consumer_sdk/test_reference_verifier.py`, `docs/contracts.md`.

Done when: reference verifier exists outside the Praetor production binary and mirrors the documented consumer pre-actuation protocol.

## Task 22 - Latency SLA and Queue Aging
Complexity: M | Depends on: Tasks 13, 17, 19

Test first:

- Provider latency beyond SLA produces `escalate(latency_sla_exceeded)`.
- Queue age beyond configured max produces `escalate(queue_aging_exceeded)`.
- Both carry `system_fault_escalation=true`.
- No alert can remain pending indefinitely without visible escalated fault.

Files: `src/praetor/engine/timeouts.py`, `src/praetor/engine/queue_policy.py`, `tests/engine/test_latency_and_queue_aging.py`.

Done when: timeout classes produce distinct Outcome Matrix fault flags.

## Task 23 - Ticket Stamp Contract Integration
Complexity: M | Depends on: Tasks 7, 12, 17

Test first:

- Stamp success preserves candidate disposition.
- Stamp failure preserves `standard_review` and adds `ticket_stamp_failed`.
- Stamp failure preserves `auto_contain` or `escalate` candidate and adds flag.
- No ledger edict while stamp attempt is in-flight.
- Unreachable ticket system treated as stamp failure.
- `unknown` recovery resends same `stamp_id`.

Files: `src/praetor/tickets/contract.py`, `tests/tickets/test_stamp_sequencing.py`.

Done when: stamp failure never promotes `standard_review` and one-disposition invariant holds.

## Task 24 - Metrics
Complexity: M | Depends on: Tasks 17-22

Test first:

- Disposition distribution increments.
- PolicyGate override rate increments.
- LLM failure metric increments per fault flag.
- Containment directive count increments.
- Queue-aging fallback increments.
- Provider and containment breaker state metrics are independent.
- Probe outcome metrics independent from production call metrics.
- Probe rate-limit metric tracks `probe_rate_limit_per_minute`.
- Stamp status metric increments.
- Health-alert delivery status metric increments.
- Feed export lag recorded per record from `ledger_commit_at` to successful write.
- p99 feed export lag and warning threshold metric exist.
- `revocation_feed_unhealthy` transition metric increments.

Files: `src/praetor/metrics/collector.py`, `src/praetor/metrics/events.py`, `tests/metrics/test_metrics.py`.

Done when: all specified metrics, including feed lag health, are implemented.

## Task 25 - Analyst Annotation Storage
Complexity: M | Depends on: Tasks 2, 4, 10

Test first:

- Annotation cross-field validation enforced in both directions.
- `reviewer_identity` is verified principal, not self-asserted.
- Annotation links to existing `decision_id`.
- Annotation does not alter prior edict hash.

Files: `src/praetor/annotations/store.py`, `tests/annotations/test_annotations.py`.

Done when: reviewer identity and schema validation are enforced.

## Task 26 - Mandatory Phase 2 Eval Harness
Complexity: L | Depends on: Tasks 13-25

Test first - mandatory scenarios present as fixture files:

1. `benign_admin_activity`: expected `standard_review`; no policy override.
2. `confirmed_malicious_sequence`: expected `auto_contain` with host target; all gates pass.
3. `incomplete_telemetry`: `auto_contain` forbidden.
4. `prompt_construction_isolation`: structural raw-source exclusion and excerpt bounds verified.
5. `never_contain_target`: expected `escalate` with never-contain fault and `system_fault_escalation=false`.
6. `provider_timeout`: expected `escalate(provider_timeout)` and `system_fault_escalation=true`.
7. `provider_refusal`: expected `escalate(provider_refusal)` and `system_fault_escalation=true`.
8. `malformed_json`: expected `escalate(provider_malformed_json)` and `system_fault_escalation=true`.
9. `duplicate_retry`: existing decision returned; no duplicate directive emitted.
10. `config_over_budget`: expected `escalate(config_over_budget)`; no LLM call.
11. `noisy_correlated_real_telemetry_placeholder`: synthetic fixture with valid FakeProvider judgment.
12. `emergency_never_contain_blocks_inflight`: live emergency entry blocks containment and writes ledger record.
13. `revocation_feed_unhealthy_blocks_autocontain: a proposed auto_contain under an unhealthy/stale feed produces escalate(revocation_feed_unhealthy) with system_fault_escalation=true; the same scenario asserts that alerts whose disposition is standard_review or escalate on grounds unrelated to containment still flow normally during feed-unhealthy mode and are not forced to escalate by feed health alone (degraded mode blocks only new auto_contain).`
14. `account_containment_feature_gate_disabled`: valid SID/provenance account proposal still escalates with `account_containment_disabled` and `system_fault_escalation=false`.

Harness exits non-zero on any safety invariant failure. `system_fault_escalation` value is asserted for every Outcome Matrix row that produces `escalate`. CI uses FakeProvider modes; exact LLM wording is not a golden output requirement.

Files: `evals/harness.py`, `evals/scenarios/*.yaml`, `evals/schemas/scenario_schema.json`, `tests/evals/test_eval_harness.py`.

Done when: all mandatory scenarios are schema-valid and feed/account feature-gate safety invariants are asserted.

## Task 27 - Real-Provider Adversarial Excerpt Probe
Complexity: M | Depends on: Tasks 14, 26

Test first:

- Integration scenario with adversarial instruction-like excerpts runs against real provider.
- Test marked `@pytest.mark.integration` and `@pytest.mark.probabilistic`.
- Results logged but not deterministic CI pass/fail.
- Docs distinguish structural prompt isolation from probabilistic real-provider resistance.

Files: `evals/real_provider_adversarial.py`, `tests/evals/test_real_provider_adversarial.py`.

Done when: scenario cannot be mistaken for a deterministic safety proof.

## Task 28 - Correlation Normalization and PromptExcerptSet
Complexity: L | Depends on: Tasks 2, 3, 15, 16

Test first:

- Sysmon fixture normalizes into typed facts with `provenance_path=sysmon_event_log` and `ambiguity_flag`.
- Security log normalizes with `provenance_path=windows_security_log`.
- Every normalized fact has `raw_source`.
- `PromptExcerptSet` produced alongside `EvidenceBundle`; excerpts are bounded and raw-source-free.
- Parent/child process relationships assembled correctly.
- Time-window filtering includes expected events and excludes noise.

Files: `src/praetor/correlation/sysmon.py`, `src/praetor/correlation/security_log.py`, `src/praetor/correlation/window.py`, `src/praetor/correlation/entities.py`, `src/praetor/correlation/excerpts.py`, `tests/correlation/test_sysmon_normalization.py`, `tests/fixtures/sysmon/`, `tests/fixtures/fixture_manifest.yaml`.

Done when: fixture telemetry produces valid `EvidenceBundle` and `PromptExcerptSet`.

## Task 28a - Production Orchestrator PolicyGate and Metrics Integration
Complexity: L | Depends on: Tasks 17-24, 26, 28 | Blocks: Task 31 / Phase 3 gate

**Phase 3 entry prerequisite:** must land before host/account `auto_contain` is trusted on real telemetry.

Depends on Task 28 by design: the integration targets the correlation-aware orchestrator, so it must not be wired into the walking-skeleton intake that Task 28 replaces — see DEC-048.

Test first:

- `process_alert_intake` emits `auto_contain` for a fully-gated judgment where all deterministic checks pass (the `engine_intake` analog of `confirmed_malicious_sequence`).
- `process_alert_intake` escalates with `never_contain_live_conflict` / `never_contain_snapshot` when the target is excluded; with `rate_limit_exceeded`, `containment_breaker_open`, and `revocation_feed_unhealthy` under those conditions.
- The single serializable emit transaction (per DEC-028) covers gate live-checks + edict + `NeverContainSnapshotRecord` + directive + idempotency + rate-limit update.
- `MetricsCollector` records disposition, policy-gate override, breaker state, and feed lag at the real call sites.
- The strict-xfail tripwire tests in `tests/engine/test_policygate_integration_tripwire.py` are converted to passing tests (markers removed).

Files: `src/praetor/engine/orchestrator.py`, `src/praetor/engine/recovery.py`, `evals/scenarios/*.yaml`, `tests/engine/*`, `tests/metrics/*`.

Done when: the production decision path enforces the full Outcome Matrix via `evaluate_policy_gate` in one serializable emit transaction, metrics are emitted from real call sites, and end-to-end `engine_intake` evals drive both a gated `auto_contain` and a never-contain block.

## Task 29 - Correlator Identity Compliance Tests
Complexity: M | Depends on: Tasks 16, 28

Test first, marked integration where real fixtures are required:

- Real Sysmon process-creation event normalizes with `provenance_path=sysmon_event_log`.
- Real Windows Security logon event normalizes with `provenance_path=windows_security_log`.
- This pair satisfies account corroboration.
- Two Sysmon facts from same scenario are rejected for account corroboration.
- `ambiguity_flag` set correctly on ambiguous facts.

Files: `tests/correlation/test_correlator_identity_compliance.py`.

Done when: real normalized shapes match synthetic eligibility tests. Passing this task is required before production account auto-containment can be enabled.

## Task 30 - Correlation Accuracy Gate
Complexity: M | Depends on: Task 28

Test first, marked integration:

- Known OTRF scenario collects expected events.
- Noise overcollection below configured threshold.
- Missing required event relationships fail the gate.
- Fixture manifest checksum verified before gate runs.

Files: `evals/correlation_gate.py`, `evals/correlation_expected/*.yaml`, `tests/evals/test_correlation_gate.py`.

Done when: correlation quality is measured before judgment is trusted on real telemetry.

## Task 31 - Phase 3 Harness on Correlated Telemetry
Complexity: M | Depends on: Tasks 26, 29, 30

Test first, marked integration:

- Harness consumes correlated `EvidenceBundle` from Task 28 output.
- `noisy_correlated_real_telemetry` runs against real OTRF fixture.
- Phase 2 safety invariants still pass on noisy real telemetry.
- Gate fails if human-authored expected output file is absent.
- Account containment production feature gate cannot be enabled unless identity compliance tests pass.

Files: `evals/run_phase3_gate.py`, `tests/evals/test_phase3_regression_gate.py`, `evals/correlation_expected/noisy_correlated_real_telemetry.yaml`.

Done when: Phase 3 cannot pass without committed human expected outputs and identity compliance evidence.

## Task 32 - Sigma Rule Repository
Complexity: M | Depends on: Task 28

Test first: Sigma rules validate syntactically; each has ATT&CK mapping; fixture event maps to at least one rule.

Files: `detections/sigma/windows/*.yml`, `detections/attack_mapping.yaml`, `tests/detections/test_sigma_rules.py`.

Done when: portable detection content exists independently of Splunk.

## Task 33 - SPL Compilation and Splunk Demo Harness
Complexity: L | Depends on: Task 32

Test first: Sigma compiles to deterministic SPL; unsupported features fail clearly; saved-search definitions generated; ingest script validates fixture paths and checksums; integration tests skip if fixtures absent.

Files: `tools/compile_sigma.py`, `detections/spl/*.spl`, `splunk/savedsearches.conf`, `splunk/props.conf`, `splunk/README.md`, `tools/splunk_ingest_demo.ps1`, `tests/splunk/test_savedsearch_generation.py`.

Done when: local Splunk Free demo path is reproducible.

## Task 34 - Empirical Org-Config Sweep Prototype
Complexity: L | Depends on: Tasks 9, 28, 30

Test first: sweep summarizes observed principals, assets, admin patterns, and frequency counts; output is proposed config artifact, not active config; report documents coverage limits and absence-of-evidence risks.

Files: `src/praetor/codification/sweep.py`, `src/praetor/codification/report.py`, `tests/codification/test_sweep.py`.

Done when: SOC lead can review proposed artifact before activation.

## Task 35 - Production Throughput Benchmark and Operator Runbooks
Complexity: L | Depends on: all target-release tasks

Test first:

- Benchmark uses provisional sustained and burst alert-rate targets defined before Sprint 1 ends.
- Full serialized SQLite path measured: prev-hash lookup, hash, insert, idempotency, rate-limit update, live never-contain check, feed-health check, and feed outbox insertion where applicable.
- Throughput ceiling documented in `docs/operator_runbook.md`.
- Docs reference generated schemas.
- Runbook covers LLM failure recovery, provider-health breaker, half-open probes, containment breaker, ledger integrity failure, revocation-feed unhealthy mode, feed ACLs, feed lag metrics, append-only JSONL capacity planning, safe archival/truncation below retention floor, chain as revocation system of record, never-contain conflict after emission, emergency race responsibility boundary, stamp recovery, non-compliant consumer residual risk, consumer pre-actuation protocol, clock skew, SQLite WAL/singleton enforcement, and account containment production feature gate.
- Runbook states append-only JSONL has no v1 rotation machinery and segmented rotation is deferred.
- All API docs use `standard_review`, not `pass`.

Files: `benchmarks/serialized_path.py`, `docs/contracts.md`, `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md`, `tests/docs/test_docs.py`.

Done when: deployment constraints are measured and a new operator can understand contracts, responsibility boundaries, feed behavior, failure modes, phase gates, and residual risks without reading source.

## Phase Gates

### Phase 1 - Durable Walking Skeleton
Required tasks: 1-12.

Pass criteria: contracts exported, hash formulas fixed, WAL enforced, singleton lock enforced, lifecycle/outboxes operational, revocation-feed projection implemented, config activation with reconciliation passing, ledger chain verified, startup recovery handles attempts/feed/outstanding directives, smoke benchmark runs against provisional targets, and no recovery path emits containment.

### Phase 2 - Judgment and Policy Discipline
Required tasks: 13-27.

Pass criteria: mandatory eval scenarios pass with FakeProvider; full Outcome Matrix enforced including `revocation_feed_unhealthy` and `account_containment_disabled`; PolicyGate blocks unsafe `auto_contain`; emergency entries evaluated live; feed health blocks new auto-containment when stale; half-open probes use synthetic canary payload; rate limits and breakers enforced independently; `standard_review` not promoted on stamp failure; metrics include feed lag; reference consumer verifier matches protocol; account corroboration synthetic tests pass; real-provider adversarial probe is probabilistic and documented. PolicyGate and metrics are validated in isolation (`policy_gate` eval runner and unit tests); production-path integration is deferred to Task 28a / Phase 3 per DEC-048 — Phase 2 is a **conditional pass** on this basis.

### Phase 3 - Correlation
Required tasks: 28-31.

Pass criteria: real telemetry normalization populates correct provenance paths; identity compliance tests confirm real shapes match synthetic tests; correlation accuracy gate passes; human-authored expected output for noisy correlated telemetry is committed; account containment production feature gate may only be enabled after these identity gates pass; PolicyGate and `MetricsCollector` are wired into `process_alert_intake` in one serializable emit transaction (DEC-028, Task 28a); end-to-end `engine_intake` evals drive a gated `auto_contain` and a never-contain block; the integration tripwire tests pass without xfail.

### Phase 4 - Detection Portability
Required tasks: 32-33.

Pass criteria: Sigma validates; ATT&CK mapping present; SPL generation deterministic; Splunk demo reproducible with checksum-verified fixtures.

### Phase 5 - Codification and Operator Readiness
Required tasks: 34-35.

Pass criteria: empirical sweep generates reviewable proposed org-config artifact; production throughput ceiling measured; operator runbook covers responsibility boundaries, revocation feed projection, feed capacity/truncation guidance, emergency race, consumer checks, account feature gate, and startup recovery.

## Deferred Work

- External CTI enrichment.
- RAG-backed similar-case retrieval.
- Cloud and Linux telemetry.
- Production WORM/external ledger storage and signed records.
- Direct SOAR/EDR actuation adapters.
- Analyst UI beyond annotation storage.
- Subnet and asset-group containment.
- Provider tokenizer API budget estimation.
- Horizontal scaling with cross-process state-store serialization.
- Revocation feed segment registry, rotation machinery, and consumer cursor registration.
- Multi-feed deployments and `revocation_feed_id` on directives.