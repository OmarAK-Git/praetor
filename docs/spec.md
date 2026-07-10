# DOCUMENT 1 - Praetor Specification

**Status:** Behavioral source of truth. v1 baseline plus **V2 mirrors** (DEC-058–063,
Gates 0–5 closed 2026-07-10). Hash/ID pins and the authoritative Outcome Matrix table
also live in `docs/contracts.md`; when both are present they must agree. Implementation
task index: `docs/plan.md` (v1) and `docs/proposals/v2_implementation_plan.md` (V2).

## Goal

Praetor is a post-detection disposition-policy engine for a SOC. A deterministic detection layer has already fired an alert; Praetor decides what should happen next.

Praetor consumes the fired alert, assembles nearby local telemetry into a normalized evidence bundle, asks an LLM to produce a structured judgment against a human-authored org configuration, and then runs deterministic policy gates before emitting a final disposition and audit record.

The product thesis is not that the model is allowed to act silently. The thesis is that model judgment can be useful if it is constrained by stable contracts, structured citations, deterministic safety controls, durable lifecycle state, and a reviewable audit trail. The intelligence is allowed to be non-deterministic; the authority to act is not.

Praetor's responsibility ends at honest directive emission and supporting safety signals: a directive accurately reflects policy and never-contain state as evaluated at emission time, carries a short expiry, embeds the relevant never-contain snapshot, and is followed by revocation records and a revocation feed entry if Praetor later detects a conflict. The downstream consumer owns receipt-to-actuation behavior, including feed freshness checks, expiry checks, local final safety checks, and failing closed when its own pre-actuation contract cannot be satisfied.

## Explicit Non-Goals

Praetor v1 is not:

- A detection engine. Detection logic runs upstream.
- A severity scorer. Praetor emits operational dispositions, not risk scores.
- A live enforcer. `auto_contain` emits a containment directive; it does not call EDR, SOAR, firewall, IAM, or cloud actuators.
- A live RPC query service for downstream consumers. v1 directives are self-contained and Praetor publishes a durable append-only revocation feed projection; consumers do not call Praetor back for never-contain state.
- An external enrichment service. VirusTotal, OTX, GeoIP, sandboxing, and CTI are deferred.
- A self-learning system. Analyst feedback affects future behavior only through deliberate SOC-lead org-config edits.
- A suppressor. There is no `auto_close`. Every alert remains visible to humans or produces a reviewable containment directive.
- A computational replay engine for LLM output. Praetor records enough information to reconstruct the case for human review; commercial providers may not reproduce identical outputs.
- An identity provider. Praetor enforces authorization on write surfaces; it does not issue, rotate, or manage tokens.
- A subnet- or asset-group-level container. v1 `auto_contain` targets hosts and, behind a production feature gate, strictly corroborated accounts.
- A revocation-feed rotation manager. v1 writes append-only JSONL with operator-managed archival/truncation guidance; segment registries and consumer cursor registration are deferred.

## Disposition Contract

Praetor emits exactly one authoritative completed `DecisionEdict` per unique tuple of `alert_id`, `evidence_bundle_hash`, and `org_config_snapshot_hash`. Identical redelivery returns the existing completed edict. Processing attempts are internal lifecycle records and do not affect the disposition count.

| Disposition | Meaning | Failure Mode If Wrong | Evidence Bar |
|---|---|---|---|
| `standard_review` | Route to normal human review. | A human still sees it. Fails safe. | Default for uncertainty, low evidence, and stamp failure that does not affect threat judgment. |
| `escalate` | Route to prioritized human review. | A human sees it sooner than necessary. Fails loud. | Correlated evidence suggests a real time-sensitive threat, or a system/policy/feed fault prevents safe lower disposition. |
| `auto_contain` | Emit a bounded containment directive before human review. | A host or account may be wrongly constrained if the consumer also acts unsafely. Fails loud and reviewable. | High-evidence convergence plus successful deterministic PolicyGate authorization and healthy revocation feed. |

`standard_review` replaces `pass` in all API, schema, enum, and persistence surfaces.

Uncertainty flows downward. A model may propose `auto_contain`, but Praetor may downgrade it if deterministic controls fail. A model may not bypass those controls.

`DecisionEdict.system_fault_escalation` is `true` when `final_disposition = escalate` was caused by an infrastructure, feed-delivery, or model-quality fault, not by an intentional policy or safety gate. `system_fault_escalation = false` on an `escalate` record means a deliberate policy or safety gate fired. Queue renderers and consumers must expose this flag so analysts can triage infrastructure failures separately from security assessments and policy-gate containment blocks.

### Outcome Matrix

Every failure class produces a specified disposition and a specific fault flag. The eval harness asserts this matrix.

| Failure class | Disposition | Fault flag | `system_fault_escalation` |
|---|---|---|---|
| Correlation failed / no bundle assembled | `escalate` | `correlation_failure` | `true` |
| Active org config exceeds hard budget | `escalate` | `config_over_budget` | `true` |
| Cited evidence ID / field path does not resolve | `escalate` | `invalid_model_citation` | `true` |
| Provider returned malformed JSON | `escalate` | `provider_malformed_json` | `true` |
| Provider timed out past bounded retry | `escalate` | `provider_timeout` | `true` |
| Provider refused | `escalate` | `provider_refusal` | `true` |
| Provider unavailable (integration/transport/upstream failure before judgment) | `escalate` | `provider_unavailable` | `true` |
| Target on snapshot never-contain list | `escalate` | `never_contain_snapshot` | `false` |
| Target on live never-contain list at emission time | `escalate` | `never_contain_live_conflict` | `false` |
| Account target with insufficient identity corroboration | `escalate` | `ambiguous_target_identity` | `false` |
| Containment target spans multiple cited hosts | `escalate` | `ambiguous_containment_target` | `false` |
| Host target with insufficient cited-evidence corroboration | `escalate` | `insufficient_corroboration` | `false` |
| Account containment production feature gate disabled | `escalate` | `account_containment_disabled` | `false` |
| Target-scoped containment rules conflict with no precedence | `escalate` | `policy_ambiguity` | `false` |
| Containment rate limit exceeded | `escalate` | `rate_limit_exceeded` | `false` |
| Containment circuit breaker open | `escalate` | `containment_breaker_open` | `false` |
| Provider-health circuit breaker open | `escalate` | `provider_health_breaker_open` | `true` |
| Revocation feed unhealthy or stale beyond propagation SLO | `escalate` | `revocation_feed_unhealthy` | `true` |
| Provider latency past SLA | `escalate` | `latency_sla_exceeded` | `true` |
| Queue age past configured max | `escalate` | `queue_aging_exceeded` | `true` |
| Ticket stamp failed | candidate preserved | `ticket_stamp_failed` | unchanged from candidate value |
| Ledger chain integrity failure at startup | refuse to start | `ledger_chain_integrity_failure` | n/a |

Policy/safety-gate faults carry `system_fault_escalation=false`. Infrastructure, model-quality, queue/latency, and revocation-feed faults carry `true`. Ticket stamp failure does not promote `standard_review` to `escalate`; it preserves the candidate disposition and adds `ticket_stamp_failed`.

## Architecture

```text
Detection Layer
  Sigma / saved search / upstream detector
        |
        v
Alert Intake
  validates AlertEnvelope, serializes attempt allocation, binds org-config snapshot
        |
        v
Correlation Layer
  local telemetry -> EvidenceBundle + PromptExcerptSet
        |
        v
Judgment Layer
  PromptExcerptSet + full OrgConfigSnapshot -> ModelJudgment
        |
        v
PolicyGate
  schema, citations, never-contain snapshot+live+emergency entries,
  identity, feature gates, containment policy, rate limits, breakers,
  revocation-feed health, latency, queue aging, expiry, idempotency
        |
        v
Durable Attempt Lifecycle + Ticket Stamp Outbox + SystemHealthAlert Outbox
        |
        v
DecisionEdict + optional ContainmentDirective
  hash-chained append-only audit log
  chain record types: DecisionEdict, DirectiveRevocationRecord,
  NeverContainSnapshotRecord, EmergencyNeverContainRecord
        |
        v
RevocationFeed Exporter
  append-only JSONL projection for consumer pre-actuation checks
        |
        v
Downstream consumer validates self-contained directive + revocation feed freshness
        |
        v
Human Governance Loop
```

Ledger append is internal-only. `SystemHealthAlert` records are in the outbox, not in the hash chain. The revocation feed is a delivery projection, not the durable system of record; the hash chain remains authoritative for audit history.

## Durable Lifecycle, Retry, and Startup Recovery

Praetor stores one authoritative per-attempt lifecycle record in SQLite. No per-alert side effect is considered to have happened unless this record durably says so.

Attempt states: `allocated -> active -> pending_stamp -> stamp_resolved -> ready_to_append -> completed`, with `aborted` reachable from any non-terminal state.

At most one non-terminal attempt may exist per `alert_id`, enforced by a serializable attempt-allocation transaction. The loser in a duplicate-intake race re-checks for an existing completed edict for the same three-tuple after acquiring the lock; it must not allocate a fresh attempt immediately after the winner completes.

Startup order before accepting intake:

1. Acquire an OS-level singleton file lock and hold for process lifetime. `flock` on POSIX; exclusive `CreateFile` on Windows. Exit non-zero if unavailable.
2. Verify SQLite initialization: required journal mode is WAL; connection isolation is explicit; `BEGIN IMMEDIATE` enforced for all critical paths. Required parameters documented in `docs/operator_runbook.md`. Exit non-zero if misconfigured.
3. Verify ledger hash-chain integrity. If broken, emit `SystemHealthAlert(ledger_chain_integrity_failure)` via the durable outbox and refuse to start.
4. Enumerate non-terminal attempts and resolve them deterministically. Recovery never emits or re-emits containment.
5. For stamp-resolved or ready-to-append attempts missing a ledger edict, append a safe completed edict reflecting recovery and recorded stamp status.
6. Reconcile idempotency keys, rate counters, breaker counters, and revocation-feed outbox rows against finalized attempts.
7. Scan outstanding unexpired `ContainmentDirective`s with no existing `DirectiveRevocationRecord` against current never-contain state, including active emergency entries. Matching directives produce `DirectiveRevocationRecord`s and `SystemHealthAlert`s before intake opens.
8. Recover pending revocation-feed rows in sequence. If recovery cannot bring the feed within propagation SLO, Praetor enters degraded non-actuating mode: intake may produce `standard_review` or `escalate`, but PolicyGate blocks new `auto_contain` with `revocation_feed_unhealthy` until feed health recovers.
9. Open full intake only after reconciliation completes and feed health is within SLO.

## Ticket Stamp Contract and Outbox

Stamping precedes ledger write. v1 uses a durable SQLite stamp outbox keyed by stable `stamp_id`.

`stamp_id` is derived by the same canonical, length-delimited construction as other hashes, using domain constant `praetor:v1:stamp_id` and the candidate decision context. Before calling the ticket system, Praetor writes a pending outbox entry. Definite responses are recorded as `succeeded` or `failed`; timeout or ambiguous responses are recorded as `unknown`, never silently failed.

The ticket integration contract requires the receiver to treat repeated `stamp_id` as idempotent no-ops. Where a backend cannot guarantee this, the residual double-stamp risk is documented.

Recovery rules: `succeeded` - append missing edict with `stamp_status = succeeded`. `unknown` - resend the same `stamp_id`; resolve to succeeded or failed based on the idempotent retry response; do not write a new stamp. `failed` - preserve candidate disposition, add `ticket_stamp_failed`, append one edict.

## Alert Intake

Alert intake receives a versioned `AlertEnvelope` and binds it to an org-config snapshot at queue time. In-flight alerts keep their assigned snapshot. The exception is the live never-contain check, including active emergency entries, immediately before directive emission.

## Correlation Layer

The correlator assembles local context: process relationships, entity activity, temporal sequence, and local movement indicators. Telemetry may contain attacker-controlled strings; facts are normalized into typed fields.

Every normalized fact in `EvidenceBundle` includes: stable evidence ID, typed normalized fields, source event reference, `raw_source`, `provenance_path`, `ambiguity_flag`, timestamp, and entity references where available.

`raw_source` is local-only. It is stored and hashed but structurally absent from the LLM prompt. The `EvidenceBundle` hash covers canonical serialization of the full bundle including `raw_source`.

## PromptExcerptSet

The provider receives only `PromptExcerptSet`. Each excerpt is keyed to evidence ID, strips control characters, and is at most 200 Unicode characters. Truncation must occur at Unicode character boundaries and must include a literal omission marker such as `[...omitting N characters]`. For high-risk unbounded fields, including command lines, scripts, and base64 blobs, excerpts use head+tail truncation. The model is explicitly told when excerpt content is incomplete.

Synthetic instruction-like log content may appear only as quoted evidence excerpt text, never as system or developer instruction text.

## Judgment Layer

The LLM emits a versioned `ModelJudgment`, not the final action. Required fields: `schema_version`, `proposed_disposition`, `cited_evidence_refs`, `key_tells`, `org_config_refs`, `benign_alternatives`, `benign_alternatives_ruled_out`, `convergence_reasoning`, `narrative`, model/provider metadata.

Citation validation is structural, not a reasoning-quality gate. It confirms referenced facts exist; it does not confirm the model reasoned correctly. A logically coherent but materially wrong judgment can pass PolicyGate; the human governance loop is the only mechanism for catching that class of error.

## PolicyGate

PolicyGate deterministically converts `ModelJudgment` into final disposition. It validates schema, citations, org-config refs, containment policy (including required `default_action` and rule precedence), host and account corroboration floors, snapshot and live never-contain state, active emergency entries, account identity, account production feature gate, rate limits, breakers, revocation-feed health, latency, queue age, expiry, idempotency, and provider faults.

Policy ambiguity is target-scoped. Preflight detects statically resolvable conflicts: rules that oppose for any target regardless of asset registry membership. Target-specific conflicts arise when a target's membership in multiple asset categories causes two rules to oppose with no precedence; these can survive preflight and are caught at gate time with `escalate(policy_ambiguity)`. Preflight and gate-time checks are complementary.

**Authorization posture (DEC-058).** `ContainmentPolicy.default_action` is required (`allow`, `deny`, or `escalate`; recommended new-deployment default: `escalate`). When no rule matches the target, PolicyGate applies `default_action` — containment is never granted by omission. A sole matching rule with `action: escalate` blocks `auto_contain` (escalate is not hint-only). Implicit v1 default-allow is retired drift.

PolicyGate records both `proposed_disposition` and `final_disposition` separately in `PolicyGateResult`. `auto_contain` is impossible unless every deterministic check passes.

For every proposed `auto_contain`, PolicyGate reads revocation-feed health inside the same serializable SQLite transaction as live never-contain evaluation, idempotency insertion, and rate-limit updates. A liveness flag alone is insufficient: the gate must compare the oldest pending revocation-feed outbox row's age, measured from `ledger_commit_at`, against `org_config.max_revocation_feed_propagation_delay_seconds`.

## Circuit Breakers

Provider-health and containment breakers are independent domains with separate thresholds, alerts, and recovery. Each is configured by `window_seconds`, `failure_threshold`, and `success_reset_threshold` in the org config. The containment breaker additionally uses the rate-limit counters for context.

**Provider-health breaker.** When open, production alerts receive `escalate(provider_health_breaker_open)`. Recovery uses explicit half-open probes triggered by SOC-lead action, a configured timer, or both. Production alerts continue to escalate during probing. Probe calls use synthetic canary content - a fixed, non-sensitive payload specified in the provider Protocol - never real alert data or org-specific information. Probe calls are rate-limited separately from production calls via `probe_rate_limit_per_minute` in the org config provider-health policy section; probe success/failure metrics are tracked independently from production call metrics. A probe failure during half-open returns the breaker to fully open and resets the success countdown to zero. `success_reset_threshold` consecutive probe successes close the breaker.

**Containment breaker.** When open, `auto_contain` is blocked but judgment still proceeds to `escalate` or `standard_review`. Rate-limit counters are not modified during a tripped period; they persist unchanged.

Breaker trips emit durable SOC-lead `SystemHealthAlert`s through the outbox.

## ContainmentDirective

`ContainmentDirective` is a versioned integration contract. Required fields: `schema_version`, `directive_id`, `decision_id`, `target_type`, `target_id`, `scope`, `evidence_refs`, `issued_at`, `expires_at`, `idempotency_key`, `actuator_constraints`, `revocation_policy`, `supersedes_directive_id` (optional), `status` (initially `proposed`, transitions to `emitted`), `live_never_contain_hash`, target-relevant never-contain entries evaluated at emission time, and `minimum_feed_sequence_at_issue`.

`minimum_feed_sequence_at_issue` is a pre-issuance freshness floor. It is the highest revocation-feed sequence number whose export to the JSONL feed was verified complete before this directive was issued — not merely assigned in a transaction whose export had not yet been confirmed. It tells consumers the minimum feed sequence Praetor had already durably published before issuing this directive. It does not satisfy the consumer's current feed freshness check.

**`target_id` format.** When `target_type = host`, `target_id` is the host identifier from the asset registry or evidence. When `target_type = account`, `target_id` is the SID from the corroborated `CanonicalAccountIdentity`. Name-based account identifiers are not used as `target_id` for account directives.

v1 target types are `host` and strictly corroborated `account`. Production account `auto_contain` remains disabled behind `account_auto_contain_enabled=false` by default. Preflight permits enabling the flag only when identity-compliance evidence is present (V2-024); the example org keeps the gate off. Host containment ships with citation-anchored targeting (DEC-052) and the host corroboration floor (DEC-059).

`expires_at` must be no more than 5 minutes after `issued_at`. Org config may choose a shorter lifetime but not a longer one. Idempotency is keyed on alert-target-scope.

### Consumer Pre-Actuation Protocol

Praetor provides freshness and revocation signals to support consumer-side safety. A compliant consumer owns the final actuation decision and must perform all checks below immediately before acting:

1. Confirm local clock-sync confidence is within `max_consumer_clock_skew_seconds` and that the directive is not expired after applying that skew bound.
2. Verify the target against the embedded emission-time never-contain entries and `live_never_contain_hash`. The consumer canonically serializes the embedded entries using the algorithm in `docs/contracts.md` and compares the resulting hash against `live_never_contain_hash`.
3. Check the revocation feed using two independent requirements: the consumer feed cursor must be at least `minimum_feed_sequence_at_issue`, and `feed_last_read_at` must be within `max_revocation_feed_propagation_delay_seconds + max_consumer_clock_skew_seconds` of the consumer-local check time.
4. Confirm no `DirectiveRevocationRecord` for the `directive_id` appears in the feed.
5. Confirm there is no overlapping directive lineage conflict for the target and scope, including supersession records.
6. Run any consumer-owned current-policy or local never-contain check required by that actuation environment.

If the feed is stale, unavailable, has a sequence gap, has a checksum/corruption failure, or the consumer cannot prove clock-sync confidence, the consumer must fail closed and surface a human-visible reason. A consumer that fires a stale, expired, revoked, unverifiable, or locally unsafe directive is operating its own actuation layer unsafely.

## RevocationFeed v1

Praetor v1 publishes an append-only JSONL revocation feed for consumer pre-actuation checks. The feed is a delivery projection of `DirectiveRevocationRecord`s already committed to the hash-chained ledger; it is not the system of record and is not the audit authority.

Each feed line is a versioned `RevocationFeedRecord` with required fields: `schema_version`, gap-free application-managed `sequence_number`, `directive_id`, `revocation_id`, external `reason_code`, `revoked_at`, `ledger_commit_at`, `record_checksum`, and optional `public_detail`. Internal revocation details may be present in the ledger but must not be exposed in the feed unless explicitly safe for consumers.

`sequence_number` is assigned in the same SQLite transaction as the `DirectiveRevocationRecord` and revocation-feed outbox insertion. Export is single-threaded and strictly sequential in v1. Export retries each pending row up to `max_feed_export_retries`; after the retry limit or a verification failure, the exporter transitions to `revocation_feed_unhealthy`, emits `SystemHealthAlert(revocation_feed_unhealthy)`, and PolicyGate blocks new `auto_contain`.

The feed propagation SLO is measured from `ledger_commit_at` to successful verified feed write. `org_config.max_revocation_feed_propagation_delay_seconds` defaults to 60 seconds and must be materially below the hard 5-minute directive lifetime. `org_config.max_consumer_clock_skew_seconds` defaults to 30 seconds and is a deployment prerequisite, not a universal time guarantee.

The checksum is for corruption detection, not tamper resistance. Tamper-evident audit integrity comes from the ledger hash chain. Feed file ACLs must restrict write access to the Praetor runtime principal and read access to authorized consumers.

v1 does not implement rotation. The operator runbook documents an expected-volume disk budget and states that old feed content may be operator-archived or truncated below a retention floor comfortably greater than the directive lifetime plus propagation and clock-skew margins without affecting consumer safety or audit completeness. Revocation history remains in the hash chain.

## Never-Contain Snapshots and Emergency Entries

### NeverContainSnapshotRecord

A versioned ledger record type, interleaved in the hash chain alongside `DecisionEdict`, `DirectiveRevocationRecord`, and `EmergencyNeverContainRecord`. Written whenever PolicyGate evaluates live never-contain state, specifically when `auto_contain` is proposed and the live check runs.

Required fields: `schema_version`, `record_type` (value `never_contain_snapshot`), `snapshot_id`, `snapshot_hash`, `snapshot_content` (the full combined list of permanent never-contain entries plus all currently active emergency entries at evaluation time), `evaluated_at`, `triggered_by_decision_id`.

`DecisionEdict.live_never_contain_hash` is the canonical hash of the corresponding `NeverContainSnapshotRecord.snapshot_content`. An investigator verifies retrospectively by locating the `NeverContainSnapshotRecord` for the given `triggered_by_decision_id` in the chain and hashing its `snapshot_content`.

### EmergencyNeverContainRecord

A versioned ledger record type, interleaved in the hash chain.

Required fields: `schema_version`, `record_type` (value `emergency_never_contain`), `entry_id`, `target_specification`, `added_by` (verified SOC-lead principal), `added_at`, `expires_at`, `audit_reason`.

SOC leads add emergency entries through the authenticated emergency surface (role soc_lead). Emergency entries can only restrict containment authority, never authorize it. Each entry is written to the ledger immediately, emits a SystemHealthAlert, participates in live never-contain evaluation under the same serializable SQLite lock as all live never-contain reads and idempotency insertions, and must be reconciled into the next full org-config activation or expire.
Synchronous conflict revocation. In the same serializable SQLite transaction that writes the EmergencyNeverContainRecord, Praetor scans all already-committed outstanding unexpired ContainmentDirectives whose target matches the new emergency entry and writes one DirectiveRevocationRecord per match, reason = never_contain_conflict, with the feed outbox row, in that same transaction. The idempotency key is not cleared for these conflict revocations — the target remains blocked, not re-eligible. The SystemHealthAlert(s) for the conflict are emitted to the durable outbox as a consequence of the commit and are not part of the chain transaction. This guarantees the ledger never durably represents the contradictory state of a target that is simultaneously on never-contain and carrying a live, unrevoked containment directive. The scan covers committed directives only; a directive whose PolicyGate live-check lock was acquired before this transaction commits is the emergency-entry race case below, governed by short expiry and the consumer revocation-feed check, not by this synchronous scan.

`expires_at` must be no more than 48 hours after `added_at`. SOC leads may choose a shorter lifetime but not a longer one.

**Emergency entry race responsibility line.** The synchronous scan above closes the already-committed-directive case to zero. The residual race is narrower: a PolicyGate that acquired its serializable live-check lock before the emergency entry commits will not see that entry, and a directive it emits a moment later will not carry the entry in its embedded entries. A directive emitted in that window will not carry the entry in its embedded entries. Praetor's obligation is to be honest about the state it evaluated, use a short directive expiry, and publish a `DirectiveRevocationRecord` plus revocation-feed entry and `SystemHealthAlert` when it later detects the conflict. Consumers own pre-actuation feed checks and any local current-policy checks.

## DirectiveRevocationRecord

A versioned ledger record type interleaved in the hash chain. Required fields: `schema_version`, `record_type` (value `directive_revocation`), `revocation_id`, `directive_id`, `reason`, external `reason_code`, `triggered_by`, `revoked_at`, `ledger_commit_at`, `idempotency_key_cleared`, and `superseded_by_directive_id` when `reason = supersession`.

Triggers:

- Post-emission never-contain conflict: record written; feed row written; `SystemHealthAlert` emitted; idempotency key not cleared.
- SOC-lead manual revocation: record written, feed row written, and idempotency key cleared in one SQLite transaction; new directive for same target subsequently possible.
- Supersession: record written with `superseded_by_directive_id`; feed row written; idempotency key not cleared.

Post-activation reconciliation runs within the activation transaction before the new config becomes active: outstanding, unexpired directives whose targets match the new never-contain list produce `DirectiveRevocationRecord`s, revocation-feed outbox rows, and SOC-lead `SystemHealthAlert`s.

## DecisionEdict

`DecisionEdict` is the authoritative decision record written to the hash-chained audit log.

The ledger chain contains exactly four interleaved record types, distinguished by `record_type`: `decision_edict`, `directive_revocation`, `never_contain_snapshot`, and `emergency_never_contain`. Chain verification is record-type-agnostic; an unrecognized `record_type` value is a chain integrity violation. `SystemHealthAlert` records are in a dedicated SQLite outbox and are not part of the chain.

Required fields: `schema_version`, `record_type` (value `decision_edict`), `decision_id`, alert reference, `EvidenceBundle` hash, `OrgConfigSnapshot` hash, `live_never_contain_hash`, `ModelJudgment`, `PolicyGateResult`, `final_disposition`, `system_fault_escalation`, optional `ContainmentDirective`, fault flags, `stamp_status`, timing metadata, ledger previous hash, ledger current hash, ticket stamp payload.

`decision_id` is a five-input SHA-256 construction fixed in `docs/contracts.md`: domain constant `praetor:v1:decision_id` first, then alert identity, evidence bundle hash (with `EMPTY_BUNDLE` substitution on correlation failure), org-config snapshot hash, and processing attempt identity, in that exact order, length-delimited. Idempotency keys use `praetor:v1:idempotency_key`. Stamp IDs use `praetor:v1:stamp_id`. No computation site may use inline domain strings.

The completed-edict uniqueness constraint is the three-tuple (alert ID, bundle hash, snapshot hash). This is the state-store idempotency key; it is not a substitute for `decision_id`, which includes attempt identity and is distinct per attempt.

## Authentication and Authorization

Externally callable authenticated write surfaces:

- Org-config activation - role `soc_lead`.
- Emergency never-contain entry - role `soc_lead`.
- Annotation submission - role `analyst`.

Ledger append, directive emission, feed export, and outbox writes are internal-only. Records carry verified principals, not self-asserted strings. Token issuance and the identity provider are operator-supplied and out of scope.

## Canonical Serialization and Hashing

A single canonical serialization algorithm covers all hashes and all ledger record types: UTC RFC3339 timestamps with exactly six fractional digits; object keys sorted lexicographically by Unicode code point; `NaN`/`Infinity` rejected; unknown fields rejected; inputs length-delimited for hash construction; deterministic across supported Python/Pydantic versions.

`EMPTY_BUNDLE` is a module-level sentinel that hashes deterministically, substituted into `decision_id` on correlation failure.

`docs/contracts.md` is the single source of truth for all domain constants, input orderings, embedded never-contain hash verification, revocation-feed record checksum, feed sequence semantics, and consumer pre-actuation procedure. No inline domain strings at any computation site.

## Ledger

The ledger is a hash-chained append-only audit log implemented in SQLite for v1. It is tamper-evident, not immutable. Production hardening adds signed records and external WORM storage.

The chain contains `DecisionEdict`, `DirectiveRevocationRecord`, `NeverContainSnapshotRecord`, and `EmergencyNeverContainRecord`. `SystemHealthAlert` records are in a dedicated outbox and are not in the chain. The revocation feed is a JSONL projection of ledger revocation records and is not authoritative for audit. An unrecognized `record_type` in the chain is a chain integrity violation.

Each append is a single serializable SQLite transaction. Startup verifies chain continuity before any new append.

## Account Containment and Identity Corroboration

Normalizers produce `CanonicalAccountIdentity` with fields: SID, domain, account name, account type, authority source, and ambiguity flag. Account `auto_contain` requires SID-backed identity. Name-only identity may support review or escalation but cannot authorize containment. When `target_type = account`, `ContainmentDirective.target_id` is the SID.

Account containment requires at least two normalized facts from distinct telemetry collection paths (`provenance_path` values), at least one of which is not an attacker-controlled command line or raw log string. For Windows/Sysmon v1, acceptable corroboration is one `sysmon_event_log` fact plus one `windows_security_log` fact. Two `sysmon_event_log` facts do not corroborate even if they differ in event type or field values. A target with `ambiguity_flag = true` and insufficient distinct-provenance corroboration produces `escalate(ambiguous_target_identity)`.

**SID eligibility (DEC-062).** `is_sid_backed` treats any non-empty, non-whitespace SID as sufficient for identity eligibility (v1 waiver). Strict Windows SID form is available via `is_valid_sid_format` (contracts §11) for directive emission and future gates; it does not yet gate eligibility.

Production account `auto_contain` remains blocked with `escalate(account_containment_disabled)` until a SOC lead explicitly enables `account_auto_contain_enabled` after identity-compliance preflight succeeds. The example org keeps the flag `false`.

## Host Corroboration Floor (DEC-059)

Corroboration is a first-class authorization concept for both host and account `auto_contain`. Before authorizing **host** `auto_contain`, the cited facts anchoring the host target (DEC-052) must satisfy:

1. **Distinct provenance** — cited facts span ≥2 distinct `provenance_path` values.
2. **Independent source** — at least one cited fact comes from a non-attacker-controllable `provenance_path` (contracts §12a table).
3. **No sole ambiguous basis** — host containment must not rest on a single cited fact when that fact has `ambiguity_flag = true`.

When any check fails, PolicyGate escalates with `insufficient_corroboration` (`system_fault_escalation = false`). Provenance trust classifications and the full pin live in `docs/contracts.md` §12a.

## Human Governance Loop

Analyst annotations include `disposition_correct`, `corrected_disposition`, comment, verified reviewer identity, and timestamp. Schema-level `@model_validator` enforces both directions: `corrected_disposition` is required when `disposition_correct = false`; it must be null when `disposition_correct = true`. Annotations do not retrain models or mutate runtime policy.

## Org Config

The org config is the human-authored statute rendered verbatim until a hard budget is reached. Selective omission is not allowed in v1.

Required v1 sections:

- Version metadata.
- Known principals and service principals.
- Assets and asset groups, each entry requiring `subnet_membership`.
- Normal admin patterns.
- Containment exclusions and never-contain lists, globally present.
- Business context.
- Containment policy with explicit rule precedence and required `default_action` (`allow` | `deny` | `escalate`; DEC-058).
- Account containment feature gate: `account_auto_contain_enabled`, default `false`.
- Directive lifetime policy: maximum 300 seconds, optionally shorter.
- Emergency never-contain policy: maximum 48 hours, optionally shorter.
- Rate-limit policy with scope values `per_host`, `per_subnet`, `per_asset_group`.
- Provider-health circuit-breaker policy with `window_seconds`, `failure_threshold`, `success_reset_threshold`, `probe_rate_limit_per_minute`.
- Containment circuit-breaker policy with `window_seconds`, `failure_threshold`, `success_reset_threshold`.
- Revocation-feed policy with `max_revocation_feed_propagation_delay_seconds` default 60 and `max_feed_export_retries`.
- Consumer clock-skew policy with `max_consumer_clock_skew_seconds` default 30.
- Latency and queue-aging policy.
- Provisional sustained and burst alert-rate targets, defined before Sprint 1 ends.

Activation preflight validates character budget, containment-rule scope/schema (`extra="forbid"`), required `default_action`, containment-rule precedence, both circuit-breaker sections, `probe_rate_limit_per_minute`, asset registry schema, global never-contain presence, rate-limit scopes, directive lifetime bound, emergency lifetime bound, feed propagation bound below directive lifetime, and clock-skew policy. Activation reconciliation runs within the activation transaction before the new config becomes active and acquires the same SQLite lock used for live never-contain evaluation.

## SystemHealthAlert Delivery

SystemHealthAlerts use a durable SQLite outbox with per-entry delivery status tracking. v1 delivers to JSONL plus console/stdout and writes attempt timestamp and result back to the outbox row. Outbox contract is structured to support future SIEM, chat, ticket, and SOAR integrations without schema changes.

Instances include `containment_breaker_open`, `provider_health_breaker_open`, `revocation_feed_unhealthy`, `ledger_chain_integrity_failure`, post-emission never-contain conflicts, and emergency never-contain entry creation.

## Detection Spine

Sigma is the portable detection format; pysigma compiles Sigma to Splunk SPL; OTRF/Mordor fixtures validate Windows/Sysmon rules without requiring Splunk; Splunk Free is a demo layer. Rules map to MITRE ATT&CK techniques.

## Tech Stack

- Python.
- Pydantic v2 for versioned contracts, strict validation, discriminated unions, JSON Schema export, and cross-field model validators.
- YAML/JSON org config.
- Provider abstraction via Python Protocol; Vertex AI Gemini initially; FakeProvider for deterministic scenarios.
- SQLite state store and hash-chained audit log; v1 single-process/single-writer; WAL journal mode required; OS singleton lock.
- Durable SQLite outboxes for ticket stamps, SystemHealthAlerts, and revocation-feed export.
- Append-only JSONL revocation feed projection for consumers.
- Sigma, pysigma, OTRF/Mordor fixtures, Splunk Free.

## Key Design Decisions

- LLM judgment is separated from final authorization. Deterministic controls authorize directive emission.
- Praetor owns honest emission-time state and timely revocation/freshness signals; consumers own receipt-to-actuation safety.
- `standard_review` is the default safe disposition.
- Auto-containment requires all deterministic controls to pass, including revocation-feed health.
- Evidence citations are structural checks, not reasoning-quality gates.
- `raw_source` is excluded from the prompt structurally, not by operator switch.
- Org config included in full; selective omission can hide global safety exclusions.
- Containment is earned by configuration: required `default_action`; no-rule targets do not reach `auto_contain` by omission; sole matching `escalate` rules block containment (DEC-058).
- Host `auto_contain` requires corroborated cited evidence (`insufficient_corroboration` otherwise; DEC-059).
- Containment scope is host by default; account requires SID-backed distinct-provenance corroboration and remains production feature-gated (`account_auto_contain_enabled`, default `false`).
- `system_fault_escalation = true` indicates infra/model/feed failure. Policy/safety-gate fault flags carry `false`.
- Half-open probe payloads are synthetic canary content specified in the provider Protocol; no real alert data transits the provider during probing.
- `NeverContainSnapshotRecord` is interleaved in the ledger chain so `live_never_contain_hash` is retrospectively verifiable without calling Praetor.
- Directive lifetime is hard-capped at 5 minutes; emergency never-contain lifetime is hard-capped at 48 hours.
- RevocationFeed v1 is append-only JSONL, no rotation machinery, and a projection rather than audit source of truth.
- Emergency never-contain provides immediate restriction authority without full activation roundtrip; the race window is a responsibility-boundary case covered by honest emission, short expiry, and revocation/feed signals.
- Provider-health and containment breakers are independent; recovery without production-alert traffic requires half-open probes.
- Authentication enforces write surface access; it does not make the ledger immutable.

## Acceptance Criteria

Praetor v1 is acceptable when:

- All named contracts are versioned Pydantic models with exported JSON Schema, including `NeverContainSnapshotRecord`, `EmergencyNeverContainRecord`, `DirectiveRevocationRecord`, and `RevocationFeedRecord`.
- The full Outcome Matrix is enforced by the eval harness with correct `system_fault_escalation` values, including `provider_unavailable`, `insufficient_corroboration`, `ambiguous_containment_target`, `revocation_feed_unhealthy`, and `account_containment_disabled`.
- One completed edict exists per alert/bundle/config tuple; duplicate intake races cannot produce duplicate edicts.
- `decision_id`, idempotency key, `stamp_id`, and feed checksum formulas are fixed in `docs/contracts.md` before hashing code ships.
- Durable attempt lifecycle, stamp outbox, health-alert outbox, revocation-feed outbox, and startup reconciliation pass crash-recovery tests.
- `auto_contain` cannot be emitted unless all deterministic checks pass, including live never-contain evaluation, active emergency entries, and revocation-feed health.
- Live never-contain evaluation, feed-health check, idempotency insertion, and rate-limit update occur in one serializable transaction.
- `ContainmentDirective.expires_at - issued_at <= 300 seconds` always holds.
- `EmergencyNeverContainRecord.expires_at - added_at <= 48 hours` always holds.
- Revocation feed sequence numbers are gap-free, assigned in the revocation transaction, and exported sequentially to append-only JSONL.
- PolicyGate blocks new `auto_contain` when pending feed rows exceed `max_revocation_feed_propagation_delay_seconds` or exporter verification fails.
- `NeverContainSnapshotRecord` is written into the ledger chain on each live evaluation; its `snapshot_content` covers combined permanent and active emergency entries.
- Emergency never-contain entries are written as `EmergencyNeverContainRecord` with required fields; race responsibility boundary is documented in the operator runbook.
- Half-open probe calls use synthetic canary payloads; probe outcome metrics are independent from production call metrics.
- `raw_source` is stored and hashed but absent from prompts; excerpts use Unicode-boundary-safe, omission-marked truncation.
- Account containment requires SID-backed `CanonicalAccountIdentity` and distinct-provenance corroboration; production account auto-containment remains feature-gated (`account_auto_contain_enabled`).
- Host containment requires citation-anchored targeting plus the host corroboration floor (DEC-052/059).
- Org config requires `containment_policy.default_action`; malformed rule scopes fail preflight (DEC-058 / V2-005).
- Three external write surfaces are authenticated and role-tagged: config activation, emergency never-contain, annotation.
- SQLite WAL journal mode, singleton enforcement, provisional Sprint 1 alert-rate targets, Task 11 smoke benchmark, and Task 33 production benchmark are documented.
- Metrics cover: dispositions, PolicyGate override rate, LLM failures per fault flag, containment directives, queue aging, both circuit-breaker domains, probe outcomes, stamp statuses, health-alert delivery, feed export lag per record, p99 feed lag, and feed unhealthy transitions.
- The mandatory Phase 2 eval harness includes all named scenarios and exits non-zero on any safety invariant failure.
- The reference consumer verifier exists outside the Praetor production binary and covers expiry, revocation, hash mismatch, feed stale, sequence gap, clock uncertainty, and overlapping lineage conflict.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM emits fluent but unsupported rationale. | Structured schema and citation checks; reasoning-quality is human-governed. |
| Model proposes unsafe containment. | Deterministic PolicyGate. |
| Prompt injection through logs. | Typed facts, raw-source exclusion, bounded excerpts, structural prompt tests; real-provider adversarial tests marked probabilistic. |
| Duplicate redelivery or crash creates duplicate edicts. | Three-tuple completed-edict uniqueness, serialized attempt allocation, durable lifecycle recovery. |
| Ticket stamp ambiguity after crash. | Stable stamp_id, durable outbox, idempotent receiver contract. |
| Provider breaker cannot recover without production traffic. | Half-open probe mode with synthetic canary payload, separate rate limit, and independent metrics. |
| Never-contain changes after directive emission. | Praetor emits short-expiry directives, embedded emission-time entries, revocation records, and feed entries; consumers own final pre-actuation freshness and local safety checks. |
| Emergency never-contain race window. | Praetor is honest about evaluated state, caps directive lifetime at 5 minutes, and publishes revocation/feed signals after detection; consumers must fail closed on stale or unavailable feed. |
| Consumer cannot discover revocation without live query API. | Append-only JSONL RevocationFeed v1 with gap-free sequence numbers, propagation SLO, and explicit stale/unavailable fail-closed contract. |
| Revocation feed grows without bound. | Feed is a projection, not system of record; operationally relevant window is bounded by directive expiry. Runbook documents capacity budget and safe archival/truncation below retention floor. |
| Revocation feed exporter fails. | Sequential outbox retry, lag metrics, health alert, degraded non-actuating mode, and PolicyGate block on `revocation_feed_unhealthy`. |
| Consumer clock skew invalidates expiry/feed freshness checks. | Configured `max_consumer_clock_skew_seconds`; consumers fail closed when sync confidence is outside bound. |
| Live never-contain hash cannot be audited later. | NeverContainSnapshotRecord interleaved in ledger chain; snapshot_content covers combined permanent and emergency entries. |
| Probe payload leaks org data. | Probe calls use synthetic canary content defined in provider Protocol; no real telemetry in probes. |
| system_fault_escalation mislabeling distorts analyst triage. | Policy/safety-gate flags carry false; infrastructure/model/feed flags carry true; semantics documented in spec and runbook. |
| Account containment misidentifies a principal. | SID-backed identity, distinct-provenance corroboration, synthetic tests, and production feature gate until Phase 3 real telemetry identity compliance passes. |
| False immutability claims. | v1 described as tamper-evident append-only, not immutable; production hardening requires signed records and WORM storage. |
| SQLite serialized path cannot meet production load. | Provisional targets set before Sprint 1 ends; Task 11 smoke benchmark and Task 33 full benchmark measure serialized path; ceiling documented in runbook. |

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