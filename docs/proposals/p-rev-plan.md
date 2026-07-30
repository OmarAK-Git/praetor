# DOCUMENT 2 — Praetor Production Ownership Implementation Plan

## Planning conventions

- Write the failing safety-boundary test before production code.
- Keep each SQLite write transaction short. Network I/O is strictly prohibited inside transactions.
- Preserve existing public contracts unless explicitly listed. Regenerate schemas.
- Complexity: **S** (up to 2 days), **M** (3–5 days), **L** (1–2 weeks).

## Task 0 — Freeze qualification profile and release-input gates

**Complexity:** S  
**Dependencies:** None

**Implementation**
- Add a release-input gate document. List `ticket_backend`, `identity_verifier`, `secret_provider`, `checkpoint_signer`, `immutable_store`, `monitoring_transport`, and `Windows_supervisor`. Assign an owner, decision deadline, and conformance environment to each. Production qualification is blocked until these are selected.
- Freeze a Qualification Profile specifying: hardware/OS/filesystem, SQLite/dependency lock hashes, configured ingress rate, inbox/outbox capacities, hard ceilings, acknowledgment p95/p99 objectives, 60-minute sustained-load duration, and recovery backlogs.
- Add fake clocks and crash-point injections to fixtures.

## Task 1 — Normative Settings, Contracts, and Schema Migrations

**Complexity:** M  
**Dependencies:** Task 0

**Implementation**
- Implement the 4-tier Settings Authority model: deployment-startup, immutable org-snapshot, live overlays, consumer-local.
- Add append-only `schema_migrations` table and executor. Ensure migrations run under the singleton lock before workers start.
- Add versioned contracts for ingress, influence, inhibition, checkpoints. Publish a contract-compatibility matrix.

## Task 2 — Extend durable state schema

**Complexity:** L  
**Dependencies:** Task 1

**Implementation**
- Add `durable_inbox`, `inbox_conflicts` (unique on `original_inbox_id, conflicting_digest`), `containment_inhibition`, `inbox_decision_links`, `influence_manifests`.
- Add 3-state DB lifecycle for files (`RESERVED -> FILE_SYNCED -> REFERENCED`).
- Implement `HELD_FOR_FEED` status for `outstanding_containment_directives`.
- Ensure WAL and `synchronous=FULL` are asserted on every connection.

## Task 3 — Implement durable inbox acceptance and Generic Conflicts

**Complexity:** M  
**Dependencies:** Task 2

**Implementation**
- Canonicalize and validate payloads before transactions.
- Implement Generic 409 conflict handling. Apply bounded retention to conflicts, use a deterministic oldest-expired-first cleanup, and maintain a digest counter on the original row if saturated. Never evict the original row.
- Link identical accepted payloads to existing `COMPLETED` three-tuple decisions via `inbox_decision_links` to prevent dual processing.

## Task 4 — Versioned Ingress Auth and Capacity Controls

**Complexity:** M  
**Dependencies:** Task 3

**Implementation**
- Add `POST /v1/alerts`, `/live`, `/ready`, `/safety`. 
- Enforce `/ready` 503 Retry-After when inbox depth exceeds the defined capacity limit.
- Implement strict versioned ingress-auth. HMAC requires timestamp, 96-bit nonce, key ID, and exact canonical string signature. mTLS must strictly strip spoofed headers if utilizing a proxy.

## Task 5 — Stage-Driven Workers and `finalize_inbox_decision`

**Complexity:** L  
**Dependencies:** Task 4

**Implementation**
- Define exactly one integration owner for the `finalize_inbox_decision(connection, ...)` transaction. All other feature branches must provide typed context overlays to this function.
- Implement inbox states: `ACCEPTED -> CLAIMED -> WAITING_PROVISIONAL_TICKET -> FINALIZING -> COMPLETED | QUARANTINED`.
- Introduce `lease_epochs` and fencing. A claim creates a boot UUID + fencing epoch lease.
- Define bounded backoff for retryable errors. Poison items quarantine only after defined limits.

## Task 6 — Clock Health Machine and AES-GCM IV/Nonce Envelopes

**Complexity:** L  
**Dependencies:** Task 5

**Implementation**
- Implement durable clock-health machine. Untrusted wall clocks halt containment and preserve directives.
- Update provenance encryption. Mandate generation of a 96-bit random IV (Nonce) per snapshot, stored unencrypted in the envelope. Validate IV presence on startup.
- Implement atomic write/fsync/rename file operations targeting the `REFERENCED` DB state.

## Task 7 — Confirmed-ticket gate and NACK Outage Handling

**Complexity:** L  
**Dependencies:** Task 5, Vendor Selection

**Implementation**
- Extend ticket protocol to 7 states (`CREATE_REQUESTED`, `CONFIRMED`, etc.).
- Enforce the ticket outage NACK rule: **Do NOT finalize as escalate.** Suspend the claim, increment attempts, and apply exponential backoff to the inbox row.
- Key authoritative upserts by decision ID.

## Task 8 — `observe_cap` Primitive and Reaffirmation

**Complexity:** L  
**Dependencies:** Task 5

**Implementation**
- Build `observe_cap(connection, context)`. Ensure it never opens/commits a transaction itself.
- Wire deferred persistence to write inhibition, alert, and ledger events on `> cap` directly from the finalizing transaction.
- Track reaffirmation intervals to prevent ledger bloat during sustained attacks.

## Task 9 — Revalidation Plan and SOC-Lead Recovery Barrier

**Complexity:** L  
**Dependencies:** Task 8

**Implementation**
- Activation plan MUST be pure revalidation. If cap is exceeded, latch and write alerts, but leave the old snapshot strictly active.
- Build the Recovery Barrier: pause claims, require IdP authorization receipt, and provide the optional Emergency Override/Bulk Revoke capability bypassing the 300-second drain.

## Task 10 — JSONL Tail Truncation and `HELD_FOR_FEED` Watermarks

**Complexity:** L  
**Dependencies:** Task 6, 8

**Implementation**
- Update exporter startup: Scrape the tail of the JSONL, auto-truncate partial/invalid records before resuming.
- Implement `HELD_FOR_FEED` delivery outbox. Release directives to consumers only when the exporter emits a checkpoint confirming the `required_feed_sequence` is durable.
- Divergent appended content triggers `HALTED`.

## Task 11 — Independent Read-Only Observer Agent

**Complexity:** L  
**Dependencies:** Task 8, 9

**Implementation**
- Write an independent read-only observer agent (e.g., separate process, reads SQLite WAL directly).
- The worker enqueues checkpoint metadata inside the ledger commit transaction. The observer reads this, constructs the payload (incorporating latch state), and signs it with keys unreadable by the Praetor worker.
- Remote store rejects True-to-False latch transitions missing SOC receipts.

## Task 12 — Queue Isolation and Bounded Executors

**Complexity:** M  
**Dependencies:** Tasks 4–11

**Implementation**
- Instantiate separate bounded worker loops: Inbox HTTP, Ticket Gate (WAITING_PROVISIONAL_TICKET), Decision Finalizer, Exporter.
- Prove that a stalled Ticket backend blocks only the Ticket Gate pool, allowing Inbox HTTP to continue until the absolute SQLite saturation limit is reached.

## Task 13 — Qualification Profile Verification

**Complexity:** L  
**Dependencies:** All prior tasks

**Implementation**
- Run full load tests against the frozen Task 0 Qualification Profile.
- Execute physical power-loss / vendor storage-flush validations to prove `synchronous=FULL` operates correctly on the target stack.
- Publish measured p95/p99 acknowledgment latency, detection, and recovery timings. Ensure failure to meet these blocks production release.

## Dependency summary

```text
Task 0 -> Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5
Tasks 6, 7, 8 follow Task 5
Task 9 follows Task 8
Task 10 follows Tasks 6, 8
Task 11 follows Tasks 8, 9
Task 12 follows Tasks 4 through 11
Task 13 follows Task 12
```

## Suggested sprint groupings

### Sprint 1 — Foundation and Stage-Driven Ownership
- Tasks 0–5. 
- Exit: Migrations, generic conflicts, `/ready` capacity limits, and the central `finalize_inbox_decision` architecture.

### Sprint 2 — Cryptography, Clocks, and Ticket Outages
- Tasks 6–7.
- Exit: AES-GCM IV envelopes, trusted clock machines, ticket 7-state logic, and backoff/NACK behavior (no fail-open).

### Sprint 3 — Caps, Recovery Barriers, and Delivery Watermarks
- Tasks 8–10.
- Exit: `observe_cap`, SOC-lead bulk override, auto-truncating JSONL, and `HELD_FOR_FEED` release logic.

### Sprint 4 — Observer Agents and Hardened Qualification
- Tasks 11–13.
- Exit: Independent WAL-scraping observer, bounded queue isolation, power-cut qualification, and signed release readiness.
