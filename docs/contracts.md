# Praetor — Contracts and Derivations (`docs/contracts.md`)

**Status: authoritative. This document is a hard prerequisite for Task 3.** No hashing, ID-derivation, feed-checksum, or canonical-serialization code may be written until the constants and constructions below are fixed here. The values in this file are the single source of truth for every computation site. If code and this document disagree, this document is correct and the code is a bug.

## What this document owns, and what it does not

This document owns the things JSON Schema cannot express and the things that produce *silent, undetectable-until-audit* divergence if defined in more than one place:

- domain-separation constants and the exact hash input orderings,
- the `decision_id`, idempotency-key, and `stamp_id` constructions,
- the canonical serialization rules,
- the revocation-feed checksum and sequence semantics,
- the consumer pre-actuation verification procedure,
- the cross-field validation rules that live in code rather than schema,
- the Outcome Matrix as the behavioral contract the eval harness asserts.

This document does **not** restate field-by-field model definitions. Those are generated as JSON Schema into `schemas/` from the Pydantic v2 models (Task 2) and are the field-level source of truth. Where a field's *meaning* or *derivation* matters beyond its type, it is described here and the schema is referenced, never duplicated. A field list copied into prose is a field list that rots; the generated schema is authoritative for shape, this document for meaning.

---

## 1. Canonical serialization

A single canonical serialization algorithm is used for every hash and every ledger record type. There is exactly one implementation (`src/praetor/hashing/canonical.py`); no computation site may serialize for hashing by any other means.

Rules:

1. **Encoding.** UTF-8, no byte-order mark.
2. **Object keys.** Sorted lexicographically by Unicode code point. Sorting is on the code point sequence, not locale-aware collation.
3. **Timestamps.** UTC, RFC3339, with exactly six fractional-second digits, `Z` suffix (e.g. `2026-05-31T20:45:00.000000Z`). A timestamp with fewer or more fractional digits is a serialization error, not silently normalized.
4. **Numbers.** `NaN` and `Infinity` (and `-Infinity`) raise `CanonicalSerializationError`. Praetor contracts should not carry floats in hashed positions; where a number is hashed it is an integer or a decimal string, never a binary float whose textual form varies.
5. **Unknown fields.** Reject. An object presented for canonical serialization that carries a field not in its schema raises an error rather than being hashed as-is. (This is stricter than Pydantic's default; canonical serialization is the strict boundary.)
6. **Absent vs null.** A field that is absent and a field explicitly set to null are distinct and serialize distinctly. Do not coerce one into the other before hashing.
7. **Determinism across versions.** The algorithm must produce identical bytes for the same logical input across all supported Python and Pydantic v2 patch versions. The test suite pins this; a serialization change that alters bytes for unchanged input is a breaking change requiring a `schema_version` bump on affected records.

`CanonicalSerializationError` is raised — never swallowed — on any rule violation. A hash is never computed over partially-serialized or fallback-serialized input.

### 1.1 Length-delimited concatenation

Every multi-input hash construction concatenates its inputs **length-delimited**, never by raw concatenation. Raw concatenation is forbidden because `("ab", "c")` and `("a", "bc")` produce identical bytes and therefore identical hashes for different logical inputs — an undetectable collision.

The delimiting construction is:

```
delimited(parts) = for each part p in order:
    utf8_bytes(decimal_length_of(p_bytes)) + ":" + p_bytes
```

That is, each part is prefixed with its byte length in ASCII decimal followed by a single `:` separator, then the part's bytes. Parts are emitted in the exact order specified by the construction; order is part of the contract and is never sorted or rearranged.

Example: `delimited(["ab", "c"])` = `2:ab1:c`, distinct from `delimited(["a", "bc"])` = `1:a2:bc`.

The domain constant is always the **first** part of any delimited construction (see §2).

---

## 2. Domain-separation constants

Domain separation prevents two different hash purposes computed over overlapping inputs from colliding. The constants are distinct ASCII strings, defined once as module-level constants in `src/praetor/hashing/domains.py`. **No computation site may use an inline domain string literal.** A grep for the literal substrings below outside `domains.py` is a review failure.

| Purpose | Constant (exact bytes) |
|---|---|
| Decision identifier | `praetor:v1:decision_id` |
| Idempotency key | `praetor:v1:idempotency_key` |
| Ticket stamp identifier | `praetor:v1:stamp_id` |

These three are deliberately distinct even though their inputs overlap. `decision_id` and the idempotency key both incorporate alert identity and hashes; a shared constant would domain-separate Praetor from non-Praetor hashes but would **not** separate these two purposes from each other, which is exactly the confusion domain separation exists to prevent.

The `vN` segment is the domain version. It is bumped only if the *construction* (input set or ordering) changes, independently of any individual record's `schema_version`. v1 is fixed for the life of the v1 release.

All three are SHA-256.

---

## 3. `decision_id`

`decision_id` is the unique identifier of a single physical `DecisionEdict` record in the ledger. It answers "which record am I looking at," and it is distinct per processing attempt.

It is **not** the deduplication key. Deduplication is the three-tuple (§5). These are orthogonal mechanisms at different layers; conflating them was explicitly rejected in design review. The three-tuple decides *whether a new attempt is allocated*; `decision_id` identifies *the record a winning attempt produces*. The disambiguating reason `decision_id` includes attempt identity: if two attempts on the same three-tuple both leave stamp-outbox entries in `unknown` state after timeouts, recovery needs attempt identity to tell the two outbox entries apart. The three-tuple alone cannot.

### Construction

```
decision_id = SHA256( delimited([
    DOMAIN_DECISION_ID,          # "praetor:v1:decision_id"  -- always first
    alert_identity,              # see §3.1
    evidence_bundle_hash,        # canonical hash, or EMPTY_BUNDLE sentinel (§6) on correlation failure
    org_config_snapshot_hash,    # canonical hash of the bound OrgConfigSnapshot
    processing_attempt_identity, # see §3.2
]) )
```

The five inputs in exactly this order. The domain constant is the first delimited part, not a prefix outside the delimiting. Output is the lowercase hex SHA-256 digest.

### 3.1 `alert_identity`

The stable identity of the upstream alert as carried on `AlertEnvelope` (field-level shape in `schemas/alert_envelope.json`). It is the SOC-assigned alert reference, canonicalized to its string form before delimiting. It is *not* Praetor's internal attempt or queue identifiers. Redelivery of the same upstream alert carries the same `alert_identity`.

### 3.2 `processing_attempt_identity`

The monotonic attempt identifier allocated by the state store (§ state store, Task 6) for the winning attempt that produced this edict. It is internal to Praetor, never supplied by the caller, and is allocated inside the serializable attempt-allocation transaction. Distinct attempts on the same three-tuple carry distinct attempt identities, which is what makes their `decision_id`s distinct.

### 3.3 Correlation-failure case

On correlation failure there is no evidence bundle. The `evidence_bundle_hash` input is the `EMPTY_BUNDLE` sentinel hash (§6), not an empty string, not a hash of an empty object. This produces a well-formed, deterministic `decision_id` for the escalate-on-correlation-failure edict. The substitution happens at exactly one place in code; every other site reads the resulting value.

---

## 4. Idempotency key

The idempotency key gates *containment directive emission*, not edict creation. It answers "is this target already under an active directive for this alert and scope." Its scope is **alert–target–scope**, deliberately not the full decision identity, so that re-judging or recorrelating the same alert does not emit a second directive for a target already under one.

### Construction

```
idempotency_key = SHA256( delimited([
    DOMAIN_IDEMPOTENCY_KEY,  # "praetor:v1:idempotency_key" -- always first
    alert_identity,          # §3.1, same canonical form as decision_id
    target_type,             # "host" | "account"
    target_id,               # §4.1
    scope,                   # the directive scope value
]) )
```

Order is fixed. The key does **not** include the evidence bundle hash or org-config snapshot hash; that is intentional. Including them would make the key change when evidence is recorrelated, defeating the purpose — a recorrelated alert must map to the *same* idempotency key so a second isolation directive is not emitted for a host already contained.

### 4.1 `target_id` in the key

- `target_type = host`: the host identifier from the asset registry or evidence.
- `target_type = account`: the **SID** from the corroborated `CanonicalAccountIdentity`. Never a name-form (`DOMAIN\user`, UPN). Two name-forms of one account must not produce two keys; the SID is the single canonical form. This is the same `target_id` written to the directive.

### 4.2 Lifecycle (clearing)

The key has states active / expired / cleared.

- A duplicate key with an **active, unexpired** directive suppresses new emission.
- An **expired** key permits a new directive carrying a supersession reference to the prior directive.
- The key is **cleared** only by SOC-lead manual revocation, in the same SQLite transaction that writes the `DirectiveRevocationRecord` — after which a new directive for that target is again possible.
- Automated revocations (never-contain conflict, supersession) write the revocation record and feed row but **do not** clear the key; the target stays blocked.

---

## 5. Completed-edict three-tuple (deduplication key)

The deduplication / "one disposition per alert" key is the tuple:

```
(alert_identity, evidence_bundle_hash, org_config_snapshot_hash)
```

This is a uniqueness constraint in the state store, checked **before** an attempt is allocated. Identical inputs return the existing completed edict; a genuinely changed bundle or config snapshot is a different tuple and legitimately produces a new decision.

This tuple is not a hash and is not `decision_id`. It is the state-store key. `decision_id` additionally includes attempt identity (§3) and is therefore distinct per attempt even for the same tuple. Both exist; neither substitutes for the other.

Intake-race rule (at-least-once delivery): at most one non-terminal attempt may exist per `alert_identity`. The loser of an allocation race, on acquiring the lock, must re-check for an existing completed edict for its tuple and return it; it must **not** allocate a fresh attempt immediately after the winner completes. "Check after acquire" is required, not optional.

---

## 6. `EMPTY_BUNDLE` sentinel

`EMPTY_BUNDLE` is a fixed module-level sentinel value representing "no evidence bundle was produced" (correlation failure). It hashes deterministically under the canonical algorithm. It is substituted into the `evidence_bundle_hash` position of `decision_id` (§3.3) on correlation failure.

It is a defined constant, not the empty string and not the hash of an empty object — both of those could collide with a real (if degenerate) bundle. Define it once, hash it once at module load, reuse the value.

---

## 7. Revocation feed: checksum and sequence semantics

The revocation feed is an append-only JSONL **projection** of `DirectiveRevocationRecord`s. It is not the system of record; the hash chain is (see spec, RevocationFeed v1). The feed exists so consumers can perform the pre-actuation revocation check (§9) without a live query API.

Field-level shape of `RevocationFeedRecord` is in `schemas/revocation_feed_record.json`. The two things that must be pinned here:

### 7.1 `record_checksum` — corruption detection, not tamper resistance

```
record_checksum = SHA256( canonical_serialization(feed_record_without_checksum_field) )
```

The checksum is computed over the canonical serialization of the feed record with the `record_checksum` field itself excluded, then the field is populated. It exists to let a consumer detect a truncated or corrupted JSONL line. It is **explicitly not** a tamper-evidence mechanism — a writer who can rewrite the line can recompute the checksum. Tamper evidence comes from the ledger hash chain, not the feed. This distinction must be stated in the operator runbook so no one mistakes feed integrity for audit integrity.

### 7.2 `sequence_number` — gap-free, assigned in the revocation transaction

- `sequence_number` is a gap-free, monotonically increasing, application-managed integer.
- It is assigned **in the same SQLite transaction** that writes the `DirectiveRevocationRecord` and the feed outbox row. The sequence is not assigned by the exporter and not by JSONL line position.
- Export is single-threaded and strictly sequential. Line N is written and verified before line N+1.
- A gap in consumed sequence numbers is, to a consumer, a feed-integrity failure that triggers fail-closed (§9).

### 7.3 `minimum_feed_sequence_at_issue` — verified-exported, not merely assigned

When a `ContainmentDirective` is issued it carries `minimum_feed_sequence_at_issue`: the **highest feed sequence whose export to JSONL was verified complete** at issuance time. It is never a sequence that was assigned in a transaction whose export had not yet been confirmed.

This precision matters: directive issuance and feed export are different transactions. If a revocation for some *other* directive is mid-export when this directive issues, setting the floor to the assigned-but-unexported sequence would cause a strict consumer to reject a legitimately fresh directive (the consumer's cursor cannot reach a sequence Praetor has not published). Using the last *verified-exported* sequence makes the floor reachable. This is a fail-closed footgun if got wrong, not a safety hole — but it degrades availability, so it is pinned here.

`minimum_feed_sequence_at_issue` is a freshness *floor* the consumer must be at or beyond; it does not by itself satisfy the consumer's current-freshness check (§9 item 3).

---

## 8. Embedded never-contain entries: consumer hash verification

Each `ContainmentDirective` embeds the target-relevant never-contain entries evaluated at emission time, plus `live_never_contain_hash`. The consumer verifies the embedded entries were not altered in transit by recomputing the hash.

### Procedure (consumer side)

```
recomputed = SHA256( canonical_serialization(embedded_never_contain_entries) )
assert recomputed == directive.live_never_contain_hash
```

The consumer canonically serializes the embedded entries using the **same** canonical algorithm defined in §1 — same key ordering, same timestamp format, same delimiting where applicable — and compares to `live_never_contain_hash`. A mismatch means the directive's embedded entries are not what Praetor evaluated; the consumer fails closed (§9 item 2).

Relationship to the ledger: `live_never_contain_hash` on the `DecisionEdict` is the canonical hash of the corresponding `NeverContainSnapshotRecord.snapshot_content` (the full combined permanent + active-emergency list at evaluation time), which is interleaved in the hash chain. An investigator verifies retrospectively by locating that snapshot record by `triggered_by_decision_id` and hashing its `snapshot_content`. The directive embeds the *target-relevant subset*; the snapshot record holds the *full* evaluated list. Both hash under §1; the consumer-side check is against the embedded subset and is for transit integrity, while the chain snapshot is for audit reconstruction.

---

## 9. Consumer pre-actuation protocol (authoritative ordering)

Praetor does not actuate. It emits honest, freshness-bearing, revocable directives; the consumer owns everything from receipt to action and must perform all of the following **immediately before** acting. This is the canonical statement of the protocol; the reference verifier (Task 21) implements exactly this and lives outside the Praetor production binary.

1. **Clock confidence + expiry.** Confirm local clock-sync confidence is within `max_consumer_clock_skew_seconds`, and that the directive is not expired after applying the skew bound. Directive lifetime is hard-capped at 300 seconds (§10); a consumer that cannot prove clock confidence fails closed.
2. **Embedded never-contain integrity.** Recompute the hash of the embedded never-contain entries (§8) and compare to `live_never_contain_hash`. Mismatch → fail closed.
3. **Feed freshness, two independent requirements.** (a) The consumer's feed cursor is at or beyond `minimum_feed_sequence_at_issue` (§7.3). (b) `feed_last_read_at` is within `max_revocation_feed_propagation_delay_seconds + max_consumer_clock_skew_seconds` of the consumer-local check time. Either failing → fail closed.
4. **No revocation.** No `DirectiveRevocationRecord` for this `directive_id` appears in the feed up to the consumer's cursor. Present → non-actionable.
5. **No lineage conflict.** No overlapping directive lineage conflict for the target and scope, including supersession records.
6. **Local policy.** Any consumer-owned current-policy or local never-contain check required by that actuation environment.

Fail-closed conditions, collectively: feed stale, feed unavailable, sequence gap, checksum/corruption failure, clock-sync unprovable, hash mismatch, or any local-policy block. On any of these the consumer must not actuate and must surface a human-visible reason. A consumer that fires a stale, expired, revoked, unverifiable, or locally unsafe directive is operating its own actuation layer unsafely; that is the consumer's responsibility, not Praetor's. The residual window — a never-contain addition after emission and before a revocation record is published, on a not-yet-expired directive — is not machine-detectable by the consumer and is the named, accepted v1 gap, bounded by the 300-second directive lifetime.

---

## 10. Hard bounds (compile-/config-time invariants)

These bounds are enforced at config-activation preflight and asserted by the eval harness. They are not advisory.

| Bound | Value | Where enforced |
|---|---|---|
| `ContainmentDirective.expires_at - issued_at` | ≤ 300 seconds | schema validator + preflight + gate |
| `EmergencyNeverContainRecord.expires_at - added_at` | ≤ 48 hours | schema validator + preflight |
| `max_revocation_feed_propagation_delay_seconds` | default 60; must be materially below 300 | preflight (must be < directive max lifetime) |
| `max_consumer_clock_skew_seconds` | default 30 | preflight; deployment prerequisite |
| `account_auto_contain_enabled` | default false | preflight; only true after Phase 3 identity gates |

Org config may choose values *more* restrictive than the directive/emergency caps (shorter lifetimes) but never less restrictive. The feed propagation delay being below the directive lifetime is a hard preflight check, not a recommendation: a propagation delay at or above the directive lifetime means a revocation could never reach a consumer before the directive it revokes expires anyway, which would make the feed pointless and is treated as misconfiguration.

---

## 11. Cross-field validation rules (enforced in code, not expressible in plain schema)

These are Pydantic v2 `@model_validator` rules at the schema level (not the storage layer). The generated JSON Schema in `schemas/` reflects field types; these *relationships* are asserted here and in the model validators, and tested in both directions.

**`AnalystAnnotation`** — both directions enforced:
- `disposition_correct = false` ⇒ `corrected_disposition` is required (non-null).
- `disposition_correct = true` ⇒ `corrected_disposition` **must be null**. "The disposition was correct, and here is a correction" is logically contradictory and must fail validation, not persist silently.

**`DirectiveRevocationRecord`**:
- `reason = supersession` ⇒ `superseded_by_directive_id` is required (non-null).
- other reasons ⇒ `superseded_by_directive_id` is null.
- `idempotency_key_cleared` is true only for the SOC-lead manual-revocation trigger; false for never-contain-conflict and supersession triggers.

**`ContainmentDirective`**:
- `target_type = account` ⇒ `target_id` is a SID (matches the SID form), never a name-form.
- `expires_at - issued_at ≤ 300s` (also §10).
- `revocation_feed_id` is **absent** in v1 (reserved post-v1); its presence is a validation error in v1.

**`EmergencyNeverContainRecord`**:
- `expires_at - added_at ≤ 48h` (also §10).

**`DecisionEdict` / Outcome Matrix coupling**: `system_fault_escalation` must equal the matrix value for the active fault flag (§12). A `final_disposition = escalate` whose fault flag is a policy/safety-gate flag with `system_fault_escalation = true` (or vice versa) is an invariant violation the eval harness must catch.

---

## 12. Outcome Matrix (behavioral contract)

The eval harness asserts, for every failure class, the disposition, the fault flag, and the `system_fault_escalation` value. `true` = infrastructure / model-quality / feed / latency-queue fault requiring operational triage. `false` = deliberate policy or safety-gate enforcement (the engine working as designed). This table is the contract; the spec's copy and this copy must match exactly.

| Failure class | Disposition | Fault flag | system_fault_escalation |
|---|---|---|---|
| Correlation failed / no bundle assembled | escalate | `correlation_failure` | true |
| Active org config exceeds hard budget | escalate | `config_over_budget` | true |
| Cited evidence ID / field path does not resolve | escalate | `invalid_model_citation` | true |
| Provider returned malformed JSON | escalate | `provider_malformed_json` | true |
| Provider timed out past bounded retry | escalate | `provider_timeout` | true |
| Provider refused | escalate | `provider_refusal` | true |
| Target on snapshot never-contain list | escalate | `never_contain_snapshot` | false |
| Target on live never-contain list at emission | escalate | `never_contain_live_conflict` | false |
| Account target, insufficient identity corroboration | escalate | `ambiguous_target_identity` | false |
| Account containment production feature gate disabled | escalate | `account_containment_disabled` | false |
| Target-scoped containment rule conflict, no precedence | escalate | `policy_ambiguity` | false |
| Containment rate limit exceeded | escalate | `rate_limit_exceeded` | false |
| Containment circuit breaker open | escalate | `containment_breaker_open` | false |
| Provider-health circuit breaker open | escalate | `provider_health_breaker_open` | true |
| Revocation feed unhealthy/stale beyond SLO | escalate | `revocation_feed_unhealthy` | true |
| Provider latency past SLA | escalate | `latency_sla_exceeded` | true |
| Queue age past configured max | escalate | `queue_aging_exceeded` | true |
| Ticket stamp failed | candidate preserved | `ticket_stamp_failed` | unchanged from candidate |
| Ledger chain integrity failure at startup | refuse to start | `ledger_chain_integrity_failure` | n/a |

Two behavioral notes the harness must assert beyond the per-row values:

- Ticket stamp failure never promotes `standard_review` to `escalate`. It preserves the candidate disposition and adds `ticket_stamp_failed`.
- `revocation_feed_unhealthy` blocks **new `auto_contain` only**. Alerts whose disposition is `standard_review` or `escalate` on grounds unrelated to containment continue to flow during feed-unhealthy degraded mode. The harness asserts the non-blocked paths still flow, not only that `auto_contain` is blocked — otherwise an implementation of "feed down ⇒ everything escalates" would pass, which is the wrong (over-restrictive) behavior.

---

## 13. Generated-schema index

Field-level shape for each contract is generated to `schemas/` and is the source of truth for field names, types, and `schema_version`. This document references them; it does not duplicate them.

- `schemas/alert_envelope.json`
- `schemas/evidence_bundle.json` (includes `provenance_path`, `raw_source`, `ambiguity_flag` per fact)
- `schemas/org_config_snapshot.json`
- `schemas/model_judgment.json`
- `schemas/policy_gate_result.json`
- `schemas/decision_edict.json`
- `schemas/containment_directive.json`
- `schemas/directive_revocation_record.json`
- `schemas/never_contain_snapshot_record.json`
- `schemas/emergency_never_contain_record.json`
- `schemas/revocation_feed_record.json`
- `schemas/system_health_alert.json`
- `schemas/analyst_annotation.json`
- `schemas/canonical_account_identity.json`

Each is exported deterministically (Task 2) and includes `schema_version`. A change to any model regenerates its schema; a change that alters canonical hashing bytes for unchanged logical input (§1 rule 7) requires a `schema_version` bump and is a breaking change.

---

## 14. Change discipline

- A change to any construction in §2–§8 bumps the relevant domain version (`praetor:v1:*` → `praetor:v2:*`) and is a breaking change; mixed-version ledgers are out of scope for v1 (unrecognized `record_type` and version drift are integrity violations, not compatibility cases).
- A change to the canonical algorithm (§1) that alters bytes for unchanged input is breaking and requires regenerating and re-versioning affected schemas.
- This document is reviewed as part of any PR that touches `src/praetor/hashing/`, contract models, the revocation feed, or the consumer protocol. Code that introduces an inline domain string, a non-delimited concatenation in a hashed position, or a second serialization path for hashing is a review failure regardless of test status.
