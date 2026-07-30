# DOCUMENT 1 — Praetor Production Ownership and Containment-Safety Specification

## 1. Goal

Extend the as-built Praetor disposition engine into a production-capable, single-writer service that safely takes durable ownership of alerts, enforces stage-driven processing isolation, and releases containment directives only when every pre-actuation control is verifiably healthy.

The release must provide:

- A durable alert inbox with strict HTTP-level capacity backpressure and exact acknowledgment boundaries.
- Retry-stable, sender-supplied idempotency with generic conflict handling.
- Stage-driven asynchronous processing (e.g., waiting for tickets vs finalizing) with safe crash recovery.
- A confirmed analyst-visible ticket before any actionable directive, with suspension/NACK on ticket outage (no fail-open).
- Transactional global enforcement of `max_outstanding_directives` utilizing an `observe_cap` primitive.
- A durable inhibition latch for detected above-cap state, clearable by a SOC-lead with an authorization receipt, allowing optional immediate bulk override.
- Consumer-side revocation cursor verification with a `HELD_FOR_FEED` delivery surface and freshness lease.
- Reconstructable model influence provenance with mandatory 96-bit Nonces (IVs) and rotation-safe cryptographic envelopes.
- An independent read-only observer agent providing ledger-tip checkpoints to detect local database tampering.
- External detection and recovery supervision independent of Praetor’s database and JSONL alert sinks.

### Success properties

1. Before acknowledgment, the alert source owns retries. Rate-limited saturation returns 503 Retry-After without silently queuing.
2. After acknowledgment, Praetor durably owns eventual processing, progressing through explicit state epochs.
3. Ticket outages backoff to the inbox; they do not fail-open into 'escalate' decisions.
4. Every final decision remains ledger-authoritative and traceable to its inbox row, policy snapshot, evidence, model context, and ticket state.
5. Host compromise cannot silently clear the inhibition latch without the independent WAL-reading observer detecting the divergence.

## 2. Explicit non-goals

- Calling EDR, SOAR, or endpoint APIs directly (`DEBT-080`).
- Active-active writers or cross-process write serialization (`DEBT-087`).
- Multi-host auto-containment (`DEBT-085`), cloud/Linux telemetry (`DEBT-083`), or policy self-tuning.
- Feed rotation or server-managed consumer registration (`DEBT-082`).
- Issuing identity tokens (`DEBT-041`). Production composition injects an approved verifier.
- Making tickets authoritative over the ledger.
- Allowing concurrent executors to block one another; stages strictly decouple I/O bounds.

## 3. Architecture

### 3.1 Component view

```text
Alert source
  -> HTTP ingress [Strict HMAC Profile / mTLS]
  -> Capacity Check -> 503 Retry-After if full
  -> DurableInbox [SQLite WAL, synchronous=FULL]
  <- 202 Acknowledgment (only after commit)

Inbox worker (Stage-driven Executor)
  -> bind immutable config snapshot / apply boot fencing
  -> correlation using trusted-clock health state machine
  -> influence snapshot: prompt + exemplars [AES-GCM + Random IV + Key ID]
  -> raw-response snapshot + influence manifest
  -> preliminary observe_cap check
  -> WAITING_PROVISIONAL_TICKET state
  -> Confirmed ticket (NACK back to inbox on outage)
  -> finalize_inbox_decision transaction:
       authoritative observe_cap / latch / feed re-check
       outstanding directive (HELD_FOR_FEED status)
       decision ledger record anchored to inbox row
       attempt and inbox stage -> COMPLETED
  -> asynchronous authoritative ticket upsert

Revocation producer
  -> checksummed revocation JSONL (tail-validated/truncated on startup)
  -> HELD_FOR_FEED -> delivery surface release after watermark checkpoint

Independent Ledger Observer (Read-Only Agent)
  -> Scrapes SQLite WAL
  -> Submits signed tip + Latch State to external immutable store
```

### 3.2 Durable inbox and acknowledgment

Introduce `src/praetor/inbox/` and an initial ASGI binding.

Each request supplies:
- Cryptographically authenticated identity via a versioned ingress-auth profile. 
  - For HMAC: requires headers for sender, key version, signed timestamp, nonce, idempotency key, and signature over `version + method + canonical path + timestamp + nonce + idempotency key + SHA-256(raw body)`. Nonces are persisted to block replay.
  - For mTLS: map SAN URI to stable sender IDs. Accept proxy identity only if proxy is explicitly authenticated and spoofable headers are stripped.
- A non-empty, retry-stable `Idempotency-Key`.

Capacity constraints:
- If the inbox depth exceeds configured saturation limits, return `503 Service Unavailable` with `Retry-After`. Do not buffer or silently drop.

Acknowledgment rules:
- Open short write transaction (WAL, `synchronous=FULL`). Insert payload, key metadata. Commit. Return HTTP 202 only after commit.

Idempotent redelivery rules:
- Same sender, same key, same digest: return original opaque receipt.
- Same sender, same key, different digest: create no new attempt. Record an `inbox_conflicts` row (unique to `original_inbox_id, conflicting_digest`). Assign one stable generic 409 conflict receipt. Manage capacity via bounded retention and deterministic oldest-expired-first cleanup. Never evict the original row.
- If an accepted inbox row correlates to an already COMPLETED three-tuple decision, atomically mark the inbox row COMPLETED, link it via `inbox_decision_links`, and append an alias-resolution ledger record. Do not rerun judgment/ticketing.

### 3.3 Asynchronous ownership and staged processing

Define inbox states: `ACCEPTED -> CLAIMED -> WAITING_PROVISIONAL_TICKET -> FINALIZING -> COMPLETED | QUARANTINED`.

- Every claim increments a `lease_epoch`. 
- Finalization requires matching `(row_id, owner_id, lease_epoch)`. Stale epochs are fenced out.
- Separate bounded executors manage stages (e.g., ticket I/O does not consume inbox claiming slots). 
- Failure classification: validation/permanent safety failures finalize as `escalate`. Retryable storage/process failures release with bounded exponential backoff. 
- Priority is determined from authenticated sender configuration.

### 3.4 Single-snapshot attempt semantics and Configuration

#### 3.4.1 Normative Settings Authorities
Configuration is explicitly stratified:
1. **Deployment-startup**: Hardware paths, worker concurrency, credentials, hard active-set ceiling. (Requires restart, applies universally).
2. **Immutable org-snapshot**: Effective outstanding cap, correlation policy. (Bound at attempt allocation, never changes mid-flight).
3. **Live safety overlays**: Emergency exclusions, inhibition latch. (Checked at the instant of deferred persistence, applies immediately to flight).
4. **Consumer-local**: Cursor storage, freshness lease duration.

#### 3.4.2 Schema Migrations
Introduce an append-only `schema_migrations` table. Run numbered, idempotent migrations holding the singleton lock before any worker starts. Never rewrite legacy snapshot payloads or hashes; provide version-specific readers. Publish a contract-compatibility matrix.

### 3.5 Trusted-clock hierarchy

Implement a durable clock-health state machine.
- Each process boot generates a UUID. Monotonic deadlines are strictly intra-boot. Worker leases use wall expiry + boot UUID + fencing epoch.
- The state machine tracks a trusted synchronization source, sampling cadence, and failure thresholds.
- If wall time is unhealthy (backward jump/drift), block auto-containment, DO NOT age unrevoked directives out of cap calculations, and use the last trusted timestamp conservatively. Recovery requires a contiguous sequence of healthy samples.

### 3.6 Influence provenance

Persist immutable influence manifests. Provide 3-state DB lifecycle for files: `RESERVED -> FILE_SYNCED -> REFERENCED`.
- Write/fsync/atomic-rename files before marking referenced. Orphan sweepers target unreferenced objects past a crash grace period.
- Snapshot Envelope MUST contain: algorithm, Key ID, **a 96-bit cryptographically secure random Nonce (IV) generated per encryption**, ciphertext, tags, plaintext length, and AAD (snapshot type, attempt ID, schema version).
- Raw provider responses must be captured exactly (UTF-8 or canonical stream) before SDK parsing.
- Investigation exports must PIN objects during read. Cleanup jobs must retry, not delete, pinned objects.

### 3.7 Confirmed-ticket gate and reconciliation

Ticket states: `CREATE_REQUESTED`, `UNKNOWN`, `LOOKUP_PENDING`, `CONFIRMED`, `FINAL_UPSERT_PENDING`, `RECONCILED`, `MISMATCH`.
- Require stable external ticket identity. Persist `CREATE_REQUESTED` prior to network call.
- **Crucial Outage Rule**: On a ticketing failure/timeout, do NOT finalize the decision as 'escalate'. Suspend the attempt, NACK back to the inbox, increment the attempt count, and apply exponential backoff. Do not fail-open a containment opportunity due to an IT service disruption.
- UNKNOWN permits lookup until a deadline. Authoritative upsert is keyed by decision ID.

### 3.8 Global outstanding-directive cap

Define a single `observe_cap(connection, context)` primitive. This function calculates the active set against the deployment hard ceiling and the snapshot effective cap but never begins/commits its own transaction.

### 3.9 Durable containment-inhibition latch

If `observe_cap` returns `> cap`, the caller's transaction writes the latch transition (`containment_inhibited=True`), health outbox, and breach ledger event. Record new ledger events only on False-to-True transitions, changes in cap/reason, or after a configured reaffirmation interval; otherwise, increment a counter.

### 3.10 Config activation and cap revalidation

Activation executes a pure revalidation plan: load bounded set, calculate outcome without writes. 
- Choose exactly one transaction outcome: If valid, apply proposal-induced revocations and activate the snapshot. 
- If proposed-cap excess occurs, write ONLY the inhibition/alert/ledger state. Leave the old snapshot active and proposal-induced directive states unchanged.

### 3.11 SOC-lead inhibition recovery

Introduce a recovery barrier: stop new claims, drain active finalizations, acquire singleton recovery guard.
- Verify the chain. 
- The recovery transaction MUST include a remotely verifiable SOC-lead authorization receipt issued by the production identity system.
- **Override clause**: The recovery protocol MUST allow the SOC lead to optionally issue an immediate bulk revocation of the active set, OR provide an explicit emergency cap override within the recovery transaction, bypassing the 300-second natural drain wait.

### 3.12 Revocation cursor and freshness lease

- Add a `HELD_FOR_FEED` delivery surface. Directives are placed in `HELD_FOR_FEED` during decision commit, noting `required_feed_sequence`. They release to consumers only after the exporter emits a checkpoint passing that watermark.
- Exporter startup MUST validate the tail of the JSONL file and automatically truncate any partial or schema-invalid trailing record before resuming appends.
- Divergent appended content triggers a `HALTED` state requiring authenticated repair.

### 3.13 Ledger checkpoints

- The external ledger checkpoint process MUST be an independent, read-only observer agent (running via the external supervisor) that directly reads the SQLite WAL. The Praetor worker DOES NOT push payloads.
- The observer submits signed tip + Latch State. 
- A latch True-to-False transition publication is rejected by the remote store unless the SOC authorization receipt and recovery record proof are valid.

### 3.14 Queue isolation and external supervision

- Endpoints: `/live` (process liveness), `/ready` (ability to authenticate/commit to inbox, respects 503 capacity limit), `/safety` (actuation status: latch, feed, ticket, provenance health).
- Executors: separate bounded loops for Inbox Claiming, Ticket Gate, Decision Finalizer, Exporter. Blockage in tickets will not stop inbox HTTP acceptance until the absolute DB limit is reached.

## 4. Technology stack

- Python 3.11+, Pydantic 2, FastAPI + Uvicorn.
- SQLite WAL (`synchronous=FULL`).
- `cryptography` AES-GCM (Strict Nonce/IV + KeyID requirement).
- Independent Read-Only Observer Agent (Go, Rust, or isolated Python process) for WAL scraping.

## 5. Key design decisions

1. **Independent Tamper Observation**: Workers don't self-report their own tampering. Observer agents read the WAL.
2. **No Ticket Fail-Open**: Backoff ensures transient ticket IT issues don't compromise security posture.
3. **Stage-Driven Ownership**: `finalize_inbox_decision` is the central convergence point. Leases are fenced by epochs.
4. **Recovery Barrier & Override**: SOC leads aren't mathematically locked out of recovery for 5 minutes during an attack.

## 6. Acceptance criteria

- A formal Qualification Profile is frozen and measured against (hardware, flush behavior, ingress rate, limits).
- 503 Retry-After is correctly emitted on capacity saturation; requests are not dropped.
- Ticket outages trigger backoff, not `escalate` bypasses.
- JSONL file tears are auto-truncated on startup.
- Snapshot envelopes failing IV presence checks reject encryption.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Storage device flush lies (`synchronous=FULL` failure) | Mandate power-cut validation on target stack in the Qualification Profile; require sign-off. |
| Attacker overwrites observer agent | Run observer in a distinct privilege context / container separated from the main worker. |

---