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
| Evidence fact identifier | `praetor:v1:evidence_id` |
| Idempotency key | `praetor:v1:idempotency_key` |
| Ticket stamp identifier | `praetor:v1:stamp_id` |

These three are deliberately distinct even though their inputs overlap. `decision_id` and the idempotency key both incorporate alert identity and hashes; a shared constant would domain-separate Praetor from non-Praetor hashes but would **not** separate these two purposes from each other, which is exactly the confusion domain separation exists to prevent.

The `vN` segment is the domain version. It is bumped only if the *construction* (input set or ordering) changes, independently of any individual record's `schema_version`. v1 is fixed for the life of the v1 release.

All three are SHA-256.

---

## 3. `decision_id`

`decision_id` is the unique identifier of a single physical `DecisionEdict` record in the ledger. It answers "which record am I looking at," and it is distinct per processing attempt.

It is **not** the deduplication key. Deduplication is the three-tuple (§6). These are orthogonal mechanisms at different layers; conflating them was explicitly rejected in design review. The three-tuple decides *whether a new attempt is allocated*; `decision_id` identifies *the record a winning attempt produces*. The disambiguating reason `decision_id` includes attempt identity: if two attempts on the same three-tuple both leave stamp-outbox entries in `unknown` state after timeouts, recovery needs attempt identity to tell the two outbox entries apart. The three-tuple alone cannot.

### Construction

```
decision_id = SHA256( delimited([
    DOMAIN_DECISION_ID,          # "praetor:v1:decision_id"  -- always first
    alert_identity,              # see §3.1
    evidence_bundle_hash,        # canonical hash, or EMPTY_BUNDLE sentinel (§7) on correlation failure
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

On correlation failure there is no evidence bundle. The `evidence_bundle_hash` input is the `EMPTY_BUNDLE` sentinel hash (§7), not an empty string, not a hash of an empty object. This produces a well-formed, deterministic `decision_id` for the escalate-on-correlation-failure edict. The substitution happens at exactly one place in code; every other site reads the resulting value.

---

## 3a. `org_config_snapshot_hash`

`org_config_snapshot_hash` is the canonical hash of the bound `OrgConfigSnapshot` **binding body** at intake/activation time. It feeds `decision_id` (§3), `stamp_id` (§5), and the completed-edict three-tuple (§6). It is **not** domain-delimited; it uses the canonical serialization algorithm (§1) only.

### Binding body

The binding body is the `OrgConfigSnapshot` record with the `snapshot_hash` field **omitted**. All other contract fields are included, including `schema_version`. No other fields may be added or dropped at hash time.

The allowed key set is fixed in `src/praetor/hashing/domains.py` as `ORG_CONFIG_SNAPSHOT_HASH_KEYS` and must match the generated `schemas/org_config_snapshot.json` property set except `snapshot_hash`.

### Construction

```
org_config_snapshot_hash = SHA256( canonical_serialize(binding_body, allowed_keys=ORG_CONFIG_SNAPSHOT_HASH_KEYS) )
```

Output is the lowercase hex SHA-256 digest. The same logical binding body must produce the same hash across calls, Python versions, and hosts.

### Verbatim judgment render and character budget

The human-authored org config file is rendered **verbatim** into the judgment context (no selective omission) per `docs/prd.md` §5 and `docs/spec.md` § Org Config. That render text is the **UTF-8 source file bytes as read from disk** (comments, whitespace, and key order preserved). Each distinct verbatim source is stored in `org_config_verbatim_renders` keyed by `(org_config_snapshot_hash, verbatim_render_id)` where `verbatim_render_id = SHA256(utf-8 source bytes)`. The active binding records which `verbatim_render_id` was used at activation; multiple verbatim sources may share one binding hash when structured content matches.

Preflight **character budget** measures the Unicode code-point length of that verbatim source text. It is **not** the canonical serialization length: two files that parse to the same structured document but differ in comments or whitespace must have different budget counts.

Structured validation and `org_config_snapshot_hash` use the parsed, defaulted, typed binding body (canonical serialize per §1). Budget and binding hash therefore serve different purposes and may diverge by design.

The v1 hard budget is `400000` characters (`HARD_CONFIG_CHARACTER_BUDGET`). Exceeding the budget is `config_over_budget` (§13).

### Snapshot persistence integrity

`org_config_snapshots` rows must satisfy: stored `snapshot_hash` equals `SHA256(canonical_serialize(binding_body))` of the stored `snapshot_json`, and the JSON `snapshot_hash` field matches the row key. Inserting an existing hash with a conflicting body is rejected. Fetch by hash rejects a mismatched JSON `snapshot_hash` field, recomputes the body hash, and calls `verify_snapshot_hash` before returning.

### Account containment gate (v1)

`account_auto_contain_enabled` defaults to `false` when omitted. In v1 Sprint 1, `account_auto_contain_enabled=true` is **rejected at preflight** — production account `auto_contain` requires Phase 3 identity compliance gates (`docs/spec.md` § RevocationFeed / account targets) that cannot be self-attested inside org config. Operators enable account containment only after those gates pass in a future phase; the org-config file cannot declare that prerequisite satisfied.

### Immutable snapshot retention

Each distinct `org_config_snapshot_hash` is stored durably with its full `OrgConfigSnapshot` JSON. In-flight processing attempts retain only the hash; the statute content must remain retrievable by hash after later activations supersede the active pointer (`docs/spec.md` § Alert Intake).

### Test vector (v1)

For the minimal valid `configs/example_org.yaml` in the repository at Task 9 completion, the binding-body hash must equal:

`8b694ab5aea32db12b6a0b89000ecb34fd1bfe8a7c70489396c18c3b9607d7d3`

---

## 3b. `evidence_id`

`evidence_id` is the stable identifier assigned to each normalized `EvidenceFact` at correlation time. It answers "which evidence fact am I citing" and is distinct per `(provenance_path, source_event_reference)` pair. Redelivery of the same upstream source event carries the same `evidence_id`.

### Construction

```
digest = SHA256( delimited([
    DOMAIN_EVIDENCE_ID,        # "praetor:v1:evidence_id" -- always first
    provenance_path,           # §3b.1
    source_event_reference,    # §3b.2
]) )

evidence_id = "ev-" + digest[:32]   # lowercase hex; first 32 digest chars only
```

Three inputs in exactly this order. The domain constant is the first delimited part. The external identifier prefixes `ev-` and truncates the digest to 32 hex characters (128 bits); the full 64-character digest is never exposed as an `evidence_id`.

Implemented in `src/praetor/correlation/ids.py` as `derive_evidence_id`; the domain constant is `DOMAIN_EVIDENCE_ID` in `src/praetor/hashing/domains.py`.

### 3b.1 `provenance_path`

The normalized provenance classifier for the fact (field-level shape in `schemas/evidence_bundle.json`). v1 values include `sysmon_event_log` and `windows_security_log` (§12a table). The string is used as-is in the preimage; it is not re-canonicalized beyond what the normalizer emits.

### 3b.2 `source_event_reference`

The canonical source-reference string for the upstream event within its collection channel. Constructed by `source_event_reference()` in `src/praetor/correlation/ids.py`:

```
channel_key = channel.split("/")[0].lower().replace(" ", "_")
source_event_reference = f"{channel_key}:{event_id}:{record_id}"
```

`event_id` is the decimal string form of the Windows EventID. `record_id` is the event's durable record identifier from the normalization layer (`event_record_id`). The channel segment before the first `/` is lowercased with spaces replaced by underscores; sub-channel suffixes (e.g. `/Operational`) are not included in the reference string.

### Test vector (v1)

For `provenance_path = sysmon_event_log` and `source_event_reference = microsoft-windows-sysmon:1:12345`:

```
evidence_id = ev-d874f190dca015a7ba7235e2e933fbd2
```

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

- A duplicate key with an **active, unexpired, unrevoked** directive suppresses new emission.
- An **expired** directive (past `expires_at`, still unrevoked) permits a **fresh** re-issue for the same alert-target-scope: same idempotency key, new `directive_id`, `supersedes_directive_id` unset, and **no** `DirectiveRevocationRecord` for the expired directive.
- **Supersession** replaces a **still-live** (outstanding, unexpired, unrevoked) directive and requires a `DirectiveRevocationRecord` with `reason = supersession`, a feed row, and `superseded_by_directive_id`; the replacement directive may set `supersedes_directive_id`. v1 PolicyGate suppresses re-issue while a directive is live via idempotency, so supersession is defined here but **not exercised** by PolicyGate in v1.
- The key is **cleared** only by SOC-lead manual revocation, in the same SQLite transaction that writes the `DirectiveRevocationRecord` — after which a new directive for that target is again possible.
- Automated revocations (never-contain conflict, supersession) write the revocation record and feed row but **do not** clear the key; the target stays blocked.

### 4.2.1 Startup reconciliation (step 6)

Startup step 6 (`reconcile_policy_state`) aligns idempotency keys with durable directive state. The following pins apply (DEC-060):

**Expired-unrevoked rows.** Rows with `revoked = 0` and `expires_at <= now` may remain in `outstanding_containment_directives` as audit residue. `fetch_outstanding_unrevoked_directives` returns only rows with `expires_at > now`, so step 6 does **not** re-register idempotency for expired directives. Fresh re-issue after natural expiry (§4.2 second bullet) does not require purging expired rows for correctness.

**Orphan outstanding directives.** A row whose `decision_id` has no matching ledger `DecisionEdict` is an orphan half-commit. Step 6 **skips** idempotency re-registration for orphans and must **not** paper over the gap by registering the key. Orphans are surfaced as an operator-visible health/audit condition (implementation: V2-010); engine startup recovery (steps 4/5) remains authoritative for the parent attempt.

---

## 5. `stamp_id`

`stamp_id` is the stable identifier of a ticket-stamp outbox entry and the idempotency key presented to the ticket integration receiver. It answers "has this logical decision already been stamped."

Unlike `decision_id` (§3), `stamp_id` is **stable across processing attempts** on the same completed-edict three-tuple (§6). Recovery on `unknown` stamp status resends the same `stamp_id` so the ticket receiver dedupes the retry as an idempotent no-op. Including `processing_attempt_identity` would produce a different `stamp_id` per attempt and cause double-stamping — that is forbidden.

### Construction

```
stamp_id = SHA256( delimited([
    DOMAIN_STAMP_ID,              # "praetor:v1:stamp_id" -- always first
    alert_identity,               # §3.1
    evidence_bundle_hash,         # canonical hash, or EMPTY_BUNDLE sentinel (§7) on correlation failure
    org_config_snapshot_hash,     # canonical hash of the bound OrgConfigSnapshot
]) )
```

Four inputs in exactly this order. The domain constant is the first delimited part. Output is the lowercase hex SHA-256 digest. The three hash inputs after the domain constant are the same tuple as the completed-edict deduplication key (§6); `processing_attempt_identity` is **not** included.

### 5.1 Rationale (stable across attempts)

Every attempt to stamp the same logical decision — same `alert_identity`, `evidence_bundle_hash`, and `org_config_snapshot_hash` — must produce an identical `stamp_id`. This includes recovery resends after crash, distinct processing attempts on the same three-tuple before completion, and any retry of an outbox entry in `unknown` state. The ticket integration contract requires the receiver to treat repeated `stamp_id` as idempotent no-ops; Praetor must never derive a new stamp identifier for the same logical decision context.

---

## 6. Completed-edict three-tuple (deduplication key)

The deduplication / "one disposition per alert" key is the tuple:

```
(alert_identity, evidence_bundle_hash, org_config_snapshot_hash)
```

This is a uniqueness constraint in the state store, checked **before** an attempt is allocated. Identical inputs return the existing completed edict; a genuinely changed bundle or config snapshot is a different tuple and legitimately produces a new decision.

This tuple is not a hash and is not `decision_id`. It is the state-store key. `decision_id` additionally includes attempt identity (§3) and is therefore distinct per attempt even for the same tuple. `stamp_id` (§5) hashes this same tuple with `DOMAIN_STAMP_ID` and is therefore identical across attempts for the same logical decision. Both exist; neither substitutes for the other.

Intake-race rule (at-least-once delivery): at most one non-terminal attempt may exist per `alert_identity`. The loser of an allocation race, on acquiring the lock, must re-check for an existing completed edict for its tuple and return it; it must **not** allocate a fresh attempt immediately after the winner completes. "Check after acquire" is required, not optional.

---

## 7. `EMPTY_BUNDLE` sentinel

`EMPTY_BUNDLE` is a fixed module-level sentinel value representing "no evidence bundle was produced" (correlation failure). It hashes deterministically under the canonical algorithm. It is substituted into the `evidence_bundle_hash` position of `decision_id` (§3.3) and `stamp_id` (§5) on correlation failure.

It is a defined constant, not the empty string and not the hash of an empty object — both of those could collide with a real (if degenerate) bundle.

### Contract preimage

The sentinel preimage string is exactly:

```
praetor:v1:empty_bundle
```

`EMPTY_BUNDLE` is `SHA256( canonical_serialization(preimage) )` — the lowercase hex digest computed once at module load in `src/praetor/hashing/canonical.py` and reused everywhere. The preimage must not change without a domain-version bump and a breaking migration.

---

## 7a. Ledger hash-chain link

The v1 ledger is a hash-chained append-only audit log (see `docs/spec.md` § Ledger). Each appended row receives a `ledger_current_hash` linking it to the prior tip. Tamper evidence comes from recomputing these links at startup and on verification walks; it is distinct from the revocation-feed `record_checksum` (§8.1), which detects corruption only.

Field-level shapes of the four interleaved record types are in `schemas/decision_edict.json`, `schemas/directive_revocation_record.json`, `schemas/never_contain_snapshot_record.json`, and `schemas/emergency_never_contain_record.json`. The link construction is pinned here.

### NeverContainSnapshotRecord append site and `snapshot_content` timing (DEC-060)

`NeverContainSnapshotRecord` is appended to the ledger **only** in the engine's terminal post-stamp `critical_transaction`, atomically paired with its `DecisionEdict` (DEC-028, DEC-053). PolicyGate is a pure evaluator and must not append ledger records. Exactly one snapshot record per qualifying edict commit — no duplicate snapshot writes inside PolicyGate.

**`snapshot_content` on the intake path (v1 contract).** The gate returns `live_never_contain_entries`: the full combined permanent + active-emergency list captured during the serializable PolicyGate evaluation (`read_live_never_contain_entries` at in-tx refresh). The engine uses that gate-supplied list as `snapshot_content` when appending the paired snapshot + edict. **Conflict rebuild paths** (e.g. deferred-directive persist conflict between gate evaluation and post-stamp commit) may refresh via `read_live_never_contain_entries` immediately before rebuilding the edict; the refreshed list is authoritative for that commit.

**Not v1.** Re-reading the live list at engine commit time on every intake path regardless of gate output would be implementation work for an owning follow-on task — current code does not generally do that on the happy path.

### Domain constant

| Purpose | Constant (exact bytes) |
|---|---|
| Ledger chain link | `praetor:v1:ledger_link` |

Defined once as `DOMAIN_LEDGER_LINK` in `src/praetor/hashing/domains.py`. No computation site may use an inline literal.

### Genesis previous-hash token

The first row in the chain has `ledger_previous_hash = null` in stored JSON (and `NULL` in the SQLite column). In the delimited link preimage, that absence is represented by the literal ASCII token:

```
null
```

Defined as `LEDGER_GENESIS_PREVIOUS_HASH` in `domains.py`. It is **not** the JSON `null` token inside the canonical body; it is the second delimited part of the link hash only.

### Body and excluded fields

```
body = canonical_serialization(record_mapping)
```

- For `record_type = decision_edict`, **`ledger_previous_hash` and `ledger_current_hash` are excluded** from the body before canonical serialization (they are outputs of the link computation, not inputs).
- For all other ledger record types, the **full contract mapping** is serialized — those types carry no embedded chain-hash fields in v1.

The body uses the canonical algorithm from §1 on Python-native values (timezone-aware `datetime` objects, not Pydantic JSON strings with imprecise fractional seconds). Stored `record_json` in SQLite is the canonical UTF-8 JSON bytes of the post-append mapping (including populated chain-hash fields on `DecisionEdict`).

### Link construction

```
ledger_current_hash = SHA256( delimited([
    DOMAIN_LEDGER_LINK,                 # always first
    ledger_previous_hash or "null",     # genesis uses LEDGER_GENESIS_PREVIOUS_HASH
    body_bytes                          # canonical_serialization(body)
]) )
```

Output is lowercase hex SHA-256. Order is part of the contract.

### Test vector (genesis link)

Minimal genesis body (`DirectiveRevocationRecord`, no chain-hash fields):

```json
{"directive_id":"dir-task010-vector","idempotency_key_cleared":true,"ledger_commit_at":"2026-06-04T12:00:00.000000Z","reason":"manual","reason_code":"manual_revocation","record_type":"directive_revocation","revocation_id":"rev-task010-vector","revoked_at":"2026-06-04T12:00:00.000000Z","schema_version":"1","superseded_by_directive_id":null,"triggered_by":"soc-lead-vector"}
```

With `ledger_previous_hash = null` (genesis):

```
ledger_current_hash = 4a702d2467a6763bfb76a23016b46d7f30cdb245514e4c3183b5d643306074e0
```

### Chain verification boundaries (v1)

- **Middle deletion** — removing any non-genesis row breaks the next row's `ledger_previous_hash` link and is detected at verification.
- **In-place tampering** — altering `record_json` or `ledger_current_hash` without recomputing the chain is detected.
- **Tail truncation** — deleting the latest row(s) leaves a prefix that still verifies internally; v1 has no anchored external tip, so tail truncation is **not detectable** from the chain alone. Production hardening (signed records, WORM storage) is out of scope for v1.

#### Optional tip anchor hook (AG-0027)

Operators may supply an out-of-band `ledger_current_hash` anchor recorded after each controlled append window. The optional verifier:

```
verify_ledger_tip_against_anchor(conn, expected_tip_hash=<hex-or-null>)
```

compares `fetch_ledger_tip_hash(conn)` to the anchor. When `expected_tip_hash` is `null`, the check is skipped. A mismatch raises `LedgerTipAnchorMismatchError` (subclass of `LedgerChainIntegrityError`). Procedure details live in `docs/operator_runbook.md`.

Unrecognized `record_type` values, malformed JSON, missing required fields, or canonical-serialization violations during verification are chain integrity failures.

---

## 8. Revocation feed: checksum and sequence semantics

The revocation feed is an append-only JSONL **projection** of `DirectiveRevocationRecord`s. It is not the system of record; the hash chain is (see spec, RevocationFeed v1). The feed exists so consumers can perform the pre-actuation revocation check (§10) without a live query API.

Field-level shape of `RevocationFeedRecord` is in `schemas/revocation_feed_record.json`. The two things that must be pinned here:

### 8.1 `record_checksum` — corruption detection, not tamper resistance

```
record_checksum = SHA256( canonical_serialization(feed_record_without_checksum_field) )
```

The checksum is computed over the canonical serialization of the feed record with the `record_checksum` field itself excluded, then the field is populated. It exists to let a consumer detect a truncated or corrupted JSONL line. It is **explicitly not** a tamper-evidence mechanism — a writer who can rewrite the line can recompute the checksum. Tamper evidence comes from the ledger hash chain, not the feed. This distinction must be stated in the operator runbook so no one mistakes feed integrity for audit integrity.

### 8.2 `sequence_number` — gap-free, assigned in the revocation transaction

- `sequence_number` is a gap-free, monotonically increasing, application-managed integer.
- It is assigned **in the same SQLite transaction** that writes the `DirectiveRevocationRecord` and the feed outbox row. The sequence is not assigned by the exporter and not by JSONL line position.
- Export is single-threaded and strictly sequential. Line N is written and verified before line N+1.
- A gap in consumed sequence numbers is, to a consumer, a feed-integrity failure that triggers fail-closed (§10).

### 8.3 `minimum_feed_sequence_at_issue` — verified-exported, not merely assigned

When a `ContainmentDirective` is issued it carries `minimum_feed_sequence_at_issue`: the **highest feed sequence whose export to JSONL was verified complete** at issuance time. It is never a sequence that was assigned in a transaction whose export had not yet been confirmed.

This precision matters: directive issuance and feed export are different transactions. If a revocation for some *other* directive is mid-export when this directive issues, setting the floor to the assigned-but-unexported sequence would cause a strict consumer to reject a legitimately fresh directive (the consumer's cursor cannot reach a sequence Praetor has not published). Using the last *verified-exported* sequence makes the floor reachable. This is a fail-closed footgun if got wrong, not a safety hole — but it degrades availability, so it is pinned here.

`minimum_feed_sequence_at_issue` is a freshness *floor* the consumer must be at or beyond; it does not by itself satisfy the consumer's current-freshness check (§10 item 3).

#### Metadata floor reconciliation (AG-0030)

`last_verified_exported_sequence` in SQLite must not outpace the on-disk `revocation_feed.jsonl`. Before export and at startup, `reconcile_feed_metadata_against_jsonl` validates the physical prefix against export metadata. If the file is missing, empty, or contains fewer verified lines than metadata claims, the feed is marked **unhealthy** immediately (`revocation_feed_unhealthy`). Rows still in `pending` state must not advance the floor (AG-0055); a fresh database yields floor `0`.

### 8.4 Supersession feed projection — consumer-local replacement linkage

`RevocationFeedRecord` intentionally omits `superseded_by_directive_id` even when the underlying `DirectiveRevocationRecord` carries it for supersession. The feed checksum allowed-key set (§8.1) and `schemas/revocation_feed_record.json` exclude that field by design.

Consumers verify a **live** supersession chain using two independent signals:

1. **Feed (revocation proof).** A feed line at or below the consumer cursor with `directive_id` equal to the superseded directive and `reason_code = supersession`.
2. **Consumer-local directive metadata (replacement proof).** The replacement `ContainmentDirective` the consumer is evaluating (or holds in its local directive store) carries `supersedes_directive_id` pointing at that superseded `directive_id`.

The feed alone cannot prove *which* replacement a supersession record refers to; pairing (1) and (2) is required. A consumer that acts on a replacement without both signals fails closed via §10 item 5 (`lineage_conflict`).

**Expired re-issue carve-out (DEC-060 §4.2).** Natural expiry is not supersession. A fresh emission after expiry reuses the idempotency key, gets a new `directive_id`, leaves `supersedes_directive_id` unset, and writes **no** `DirectiveRevocationRecord` or feed row for the expired directive. Consumers therefore must not expect a supersession feed line when evaluating such a replacement.

### 8.5 V2 feed delivery boundaries (roadmap-deferred)

V2 preserves the v1 revocation-feed delivery model. Praetor does **not** ship:

- **Rotation machinery** — v2 has **no rotation machinery**; the feed remains append-only JSONL with operator-managed archival/truncation below a retention floor (see `docs/operator_runbook.md`).
- **Feed segment registry or consumer cursor registration** — consumers track their own cursor; Praetor does not register or reconcile consumer positions.
- **Multi-feed deployments or `revocation_feed_id` on directives** — v2 assumes a single revocation feed projection per deployment.

These capabilities are explicit P5 roadmap items in `docs/proposals/delivery_backlog.md`. The hash-chained ledger remains authoritative; feed file retention is a consumer-freshness concern, not an audit completeness requirement.

---

## 9. Embedded never-contain entries: consumer hash verification

Each `ContainmentDirective` embeds the target-relevant never-contain entries evaluated at emission time, plus `live_never_contain_hash`. The consumer verifies the embedded entries were not altered in transit by recomputing the hash.

### Procedure (consumer side)

```
recomputed = SHA256( canonical_serialization(embedded_never_contain_entries) )
assert recomputed == directive.live_never_contain_hash
```

The consumer canonically serializes the embedded entries using the **same** canonical algorithm defined in §1 — same key ordering, same timestamp format, same delimiting where applicable — and compares to `live_never_contain_hash`. A mismatch means the directive's embedded entries are not what Praetor evaluated; the consumer fails closed (§10 item 2).

Relationship to the ledger: `live_never_contain_hash` on the `DecisionEdict` is the canonical hash of the corresponding `NeverContainSnapshotRecord.snapshot_content` (the full combined permanent + active-emergency list at evaluation time), which is interleaved in the hash chain. An investigator verifies retrospectively by locating that snapshot record by `triggered_by_decision_id` and hashing its `snapshot_content`. The directive embeds the *target-relevant subset*; the snapshot record holds the *full* evaluated list. Both hash under §1; the consumer-side check is against the embedded subset and is for transit integrity, while the chain snapshot is for audit reconstruction.

---

## 10. Consumer pre-actuation protocol (authoritative ordering)

Praetor does not actuate. It emits honest, freshness-bearing, revocable directives; the consumer owns everything from receipt to action and must perform all of the following **immediately before** acting. This is the canonical statement of the protocol; the reference verifier (Task 21) implements exactly this and lives outside the Praetor production binary.

1. **Clock confidence + expiry.** Confirm local clock-sync confidence is within `max_consumer_clock_skew_seconds`, and that the directive is not expired after applying the skew bound. Directive lifetime is hard-capped at 300 seconds (§11); a consumer that cannot prove clock confidence fails closed.
2. **Embedded never-contain integrity.** Recompute the hash of the embedded never-contain entries (§9) and compare to `live_never_contain_hash`. Mismatch → fail closed.
3. **Feed freshness, two independent requirements.** (a) The consumer's feed cursor is at or beyond `minimum_feed_sequence_at_issue` (§8.3). (b) `feed_last_read_at` is within `max_revocation_feed_propagation_delay_seconds + max_consumer_clock_skew_seconds` of the consumer-local check time. Either failing → fail closed.
4. **No revocation.** No `DirectiveRevocationRecord` for this `directive_id` appears in the feed up to the consumer's cursor. Present → non-actionable.
5. **No lineage conflict.** No overlapping directive lineage conflict for the target and scope, including supersession records.
6. **Local policy (§10.6, consumer-owned).** Any consumer-owned current-policy or local never-contain check required by that actuation environment. The reference verifier (`consumer_sdk/reference_verifier.py`) implements items 1–5 only; item 6 is intentionally out of reference scope and must be wired by each integrator.

Fail-closed conditions, collectively: feed stale, feed unavailable, sequence gap, checksum/corruption failure, clock-sync unprovable, hash mismatch, or any local-policy block. On any of these the consumer must not actuate and must surface a human-visible reason. A consumer that fires a stale, expired, revoked, unverifiable, or locally unsafe directive is operating its own actuation layer unsafely; that is the consumer's responsibility, not Praetor's. The residual window — a never-contain addition after emission and before a revocation record is published, on a not-yet-expired directive — is not machine-detectable by the consumer and is the named, accepted v1 gap, bounded by the 300-second directive lifetime.

---

## 11. Hard bounds (compile-/config-time invariants)

These bounds are enforced at config-activation preflight and asserted by the eval harness. They are not advisory.

| Bound | Value | Where enforced |
|---|---|---|
| `ContainmentDirective.expires_at - issued_at` | ≤ 300 seconds | schema validator + preflight + gate |
| `EmergencyNeverContainRecord.expires_at - added_at` | ≤ 48 hours | schema validator + preflight |
| `max_revocation_feed_propagation_delay_seconds` | default 60; must be materially below 300 | preflight (must be < directive max lifetime) |
| `max_consumer_clock_skew_seconds` | default 30 | preflight; deployment prerequisite |
| `account_auto_contain_enabled` | default false; `true` rejected in v1 | preflight (`account_containment_prerequisite`) |
| Org config judgment render (Unicode characters) | ≤ `400000` (`HARD_CONFIG_CHARACTER_BUDGET`) | preflight (`config_over_budget`) |
| `provisional_alert_rate_targets.sustained_alerts_per_minute` | required positive integer (v1 Sprint 1 provisional target) | preflight |
| `provisional_alert_rate_targets.burst_alerts_per_minute` | required positive integer (v1 Sprint 1 provisional target) | preflight |
| `revocation_feed_policy.max_revocation_feed_propagation_delay_seconds` | default `60` when section present and field omitted | field default at preflight only |
| `revocation_feed_policy.max_feed_export_retries` | required positive integer when section present | preflight |
| `consumer_clock_skew_policy.max_consumer_clock_skew_seconds` | default `30` when section present and field omitted | field default at preflight only |

Org config may choose values *more* restrictive than the directive/emergency caps (shorter lifetimes) but never less restrictive. The feed propagation delay being below the directive lifetime is a hard preflight check, not a recommendation: a propagation delay at or above the directive lifetime means a revocation could never reach a consumer before the directive it revokes expires anyway, which would make the feed pointless and is treated as misconfiguration.

---

## 12. Cross-field validation rules (enforced in code, not expressible in plain schema)

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
- `expires_at - issued_at ≤ 300s` (also §11).
- `revocation_feed_id` is **absent** in v1 (reserved post-v1); its presence is a validation error in v1.

**`EmergencyNeverContainRecord`**:
- `expires_at - added_at ≤ 48h` (also §11).

**`DecisionEdict` / Outcome Matrix coupling**: `system_fault_escalation` must equal the matrix value for the active fault flag (§13). A `final_disposition = escalate` whose fault flag is a policy/safety-gate flag with `system_fault_escalation = true` (or vice versa) is an invariant violation the eval harness must catch.

---

## 12a. Containment evidence corroboration (host and account)

Corroboration is a **first-class authorization concept** for `auto_contain`, not an account-only rule (DEC-059). PolicyGate evaluates corroboration on **resolved citation metadata** (`provenance_path`, `ambiguity_flag`) from `validate_evidence_citations` — the same fields the citation validator already resolves today.

### Provenance-path trust classification (v1 Windows)

| `provenance_path` | Attacker-controllable | Rationale |
|---|---|---|
| `sysmon_event_log` | **yes** | Process-creation and command-line content is injectable or spoofable in the event payload |
| `windows_security_log` | **no** | Independent Windows Security channel authentication events; distinct collection path from Sysmon |

**Default for future normalizers:** any `provenance_path` not listed in this table is **attacker-controllable** until explicitly classified here (fail-closed). Adding a non-attacker-controllable path requires a `docs/contracts.md` update before the normalizer ships.

### Account `auto_contain` corroboration (unchanged v1)

Account containment authorization requires the cited facts (or the account-identity facts the gate evaluates) to include:

- at least **two distinct** `provenance_path` values, and
- at least **one** from a **non-attacker-controllable** path per the table above.

For v1 Windows/Sysmon, the approved pair is one `sysmon_event_log` fact plus one `windows_security_log` fact. Two facts sharing the same `provenance_path` do not corroborate.

When a SID-backed account target fails this check, PolicyGate escalates with fault flag **`ambiguous_target_identity`** (`system_fault_escalation = false`). This path is unchanged from v1.

### Host `auto_contain` corroboration floor (V2)

Before authorizing host `auto_contain`, the **cited facts** anchoring the host target (DEC-052) must satisfy:

1. **Distinct provenance** — cited facts span **≥2 distinct** `provenance_path` values.
2. **Independent source** — at least **one** cited fact comes from a **non-attacker-controllable** `provenance_path` per the table above.
3. **No sole ambiguous basis** — host containment must not rest on a **single** cited fact when that fact has `ambiguity_flag = true`.

When any check fails, PolicyGate escalates with fault flag **`insufficient_corroboration`** (`system_fault_escalation = false`, policy/safety-gate class). Implementation: V2-011.

**Scope note.** Host corroboration applies to **host** containment targets after citation-anchored target resolution. It does not replace account identity corroboration or multi-host ambiguity (`ambiguous_containment_target`).

---

## 13. Outcome Matrix (behavioral contract)

The eval harness asserts, for every failure class, the disposition, the fault flag, and the `system_fault_escalation` value. `true` = infrastructure / model-quality / feed / latency-queue fault requiring operational triage. `false` = deliberate policy or safety-gate enforcement (the engine working as designed). This table is the authoritative contract. The frozen `docs/spec.md` §Outcome Matrix mirror is deferred until spec unfreeze (DEC-052); until then, this section carries rows not yet mirrored in the spec — `ambiguous_containment_target`, `insufficient_corroboration` — to be reconciled when the spec unfreezes.

| Failure class | Disposition | Fault flag | system_fault_escalation |
|---|---|---|---|
| Correlation failed / no bundle assembled | escalate | `correlation_failure` | true |
| Active org config exceeds hard budget | escalate | `config_over_budget` | true |
| Cited evidence ID / field path does not resolve | escalate | `invalid_model_citation` | true |
| Provider returned malformed JSON | escalate | `provider_malformed_json` | true |
| Provider timed out past bounded retry | escalate | `provider_timeout` | true |
| Provider refused | escalate | `provider_refusal` | true |
| Provider unavailable (integration/transport/upstream failure before judgment) | escalate | `provider_unavailable` | true |
| Target on snapshot never-contain list | escalate | `never_contain_snapshot` | false |
| Target on live never-contain list at emission | escalate | `never_contain_live_conflict` | false |
| Account target, insufficient identity corroboration | escalate | `ambiguous_target_identity` | false |
| Containment target spans multiple cited hosts | escalate | `ambiguous_containment_target` | false |
| Host target, insufficient cited-evidence corroboration | escalate | `insufficient_corroboration` | false |
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

### Metrics snapshot (Task 24)

In-process metrics (`src/praetor/metrics/`) export a `MetricsSnapshot` with these canonical key rules:

- **Disposition counts** use `Disposition` enum `.value` strings. `record_policy_gate_result` records the final disposition; callers must not also call `record_disposition` for the same gated alert.
- **LLM failure counters** key on Outcome Matrix fault flags (§13 table); unknown flags are rejected.
- **Queue aging** counter is `queue_aging_exceeded_total` (Outcome Matrix row `queue_aging_exceeded`).
- **Breaker metrics** track closed→open edges in `breaker_open_transitions`, open→closed recoveries in `breaker_recovery_transitions`, and current open state in `breaker_currently_open` per `BreakerMetricDomain`.
- **Stamp status** keys use `StampStatus` enum `.value`; terminal vs non-terminal views derive from `TERMINAL_STAMP_STATUSES` in `tickets/outbox.py`.
- **Health-alert delivery** is nested `health_alert_delivery_by_channel[channel][status]` where `channel ∈ {"jsonl","stdout"}` and `status ∈ {"succeeded","failed"}` only (`DeliveryStatus`; `pending` is not a recorded outcome).
- **Feed export lag** retains the most recent `DEFAULT_FEED_LAG_SAMPLE_WINDOW` (1000) samples; p99 uses nearest-rank on that window; `feed_export_lag_warning_exceeded` is true when p99 ≥ configured threshold.

---

## 14. Generated-schema index

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

Each is exported deterministically (Task 2) and includes `schema_version`. Regenerate with `python tools/schema_export.py --write`; CI and contract guards run `python tools/schema_export.py --check` to detect drift. A change to any model regenerates its schema; a change that alters canonical hashing bytes for unchanged logical input (§1 rule 7) requires a `schema_version` bump and is a breaking change.

---

## 15. Throughput measurement

Sprint 1 provisional alert-rate targets (`provisional_alert_rate_targets` on `OrgConfigSnapshot`, shape in `schemas/org_config_snapshot.json`) are compared against:

- **Smoke benchmark** (`benchmarks/smoke_serialized_path.py`) — revocation write + feed outbox path.
- **Production benchmark** (`benchmarks/serialized_path.py`) — DEC-053 post-stamp path: PolicyGate with `persist_directive=False`, then one engine transaction for deferred directive persist + ledger append (no per-alert revocation).

Measured ceilings and deployment interpretation are documented in `docs/operator_runbook.md` (not duplicated here).

---

## 16. Change discipline

- A change to any construction in §2–§9 bumps the relevant domain version (`praetor:v1:*` → `praetor:v2:*`) and is a breaking change; mixed-version ledgers are out of scope for v1 (unrecognized `record_type` and version drift are integrity violations, not compatibility cases). A change to the `EMPTY_BUNDLE` preimage (§7) is a breaking change requiring the same discipline.
- A change to the canonical algorithm (§1) that alters bytes for unchanged input is breaking and requires regenerating and re-versioning affected schemas.
- This document is reviewed as part of any PR that touches `src/praetor/hashing/`, contract models, the revocation feed, or the consumer protocol. Code that introduces an inline domain string, a non-delimited concatenation in a hashed position, or a second serialization path for hashing is a review failure regardless of test status.
