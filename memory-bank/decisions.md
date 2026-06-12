# Decisions

Product and architecture decisions are **documented in `docs/prd.md`** (seven numbered decisions) and **`docs/spec.md`** (Key Design Decisions). This table indexes them for agents; rationale detail stays in docs.

| ID | Date | Decision | Rationale (short) | Source |
|---|---|---|---|---|
| DEC-001 | Unknown | Model recommends; PolicyGate authorizes | Audit must separate proposal from authorization | `docs/prd.md` §1 |
| DEC-002 | Unknown | Three dispositions only; no `auto_close` | Auto-close failure mode is silent blind spot | `docs/prd.md` §2 |
| DEC-003 | Unknown | `auto_contain` requires deterministic gates | Wrong containment is asymmetric; bar to act must be inspectable | `docs/prd.md` §3 |
| DEC-004 | Unknown | Schema-enforced citations to real bundle facts | Survive hallucination; reduce prompt-injection surface | `docs/prd.md` §4 |
| DEC-005 | Unknown | Org config rendered in full until hard budget | Selective omission can drop safety exclusions | `docs/prd.md` §5 |
| DEC-006 | Unknown | Analyst feedback human-gated via config edits | No self-tuning containment authority | `docs/prd.md` §6 |
| DEC-007 | Unknown | Ledger tamper-evident; human reconstructable case | Do not overclaim immutable or LLM replay | `docs/prd.md` §7 |
| DEC-008 | Unknown | `docs/contracts.md` is SSOT for hashes/IDs/Outcome Matrix | Prevents silent cross-site divergence | `docs/contracts.md` header |
| DEC-009 | Unknown | Completed-edict key ≠ `decision_id` | Three-tuple dedupes; attempt identity in `decision_id` | `docs/contracts.md` §3, §6 |
| DEC-010 | Unknown | Revocation feed is projection; chain is audit authority | Feed checksum is corruption-only, not tamper evidence | `docs/spec.md`, `docs/contracts.md` §8 |
| DEC-011 | Unknown | `standard_review` replaces `pass` | Terminology alignment across API/schema/persistence | `docs/spec.md` |
| DEC-012 | Unknown | Account `auto_contain` gated until Phase 3 | SID + distinct-provenance corroboration required | `docs/spec.md`, `docs/plan.md` Phase 3 |
| DEC-013 | 2026-06-01 | `stamp_id` = three-tuple + `DOMAIN_STAMP_ID`; excludes attempt identity | Stable across attempts for ticket receiver idempotency on recovery resend | `docs/contracts.md` §5 |
| DEC-014 | 2026-06-01 | `EMPTY_BUNDLE` preimage = `praetor:v1:empty_bundle` | Ratified in §7; hash permanent in correlation-failure IDs | `docs/contracts.md` §7 |
| DEC-015 | 2026-06-01 | Auth via pluggable `TokenVerifier`; surfaces as Python callables | Token issuance/IdP out of scope per spec; HTTP deferred | `docs/spec.md` § Auth, TASK-004 |
| DEC-016 | 2026-06-01 | Startup guard: WAL verify-only (no auto-migrate); `isolation_level=None`; `critical_transaction` = BEGIN IMMEDIATE | Matches spec startup order steps 1–2; runbook PRAGMA list absent. TASK-005 reopen added `synchronous>=NORMAL` verification and matching `init_state_dir` bootstrap-set (guard verify-only; bootstrap sets both WAL and NORMAL). | TASK-005, `docs/spec.md` |
| DEC-017 | 2026-06-01 | `init_state_dir(db_path)` ships in Task 5 as separate one-shot WAL bootstrap | Fresh deploy must boot; guard stays verify-only; Task 6 assumes initialized DB | TASK-005 reopen, `docs/spec.md` § startup |
| DEC-018 | 2026-06-01 | Nested `critical_transaction` forbidden (raises), not nested via SAVEPOINT | Prevents silent outer-tx rollback corruption under `isolation_level=None` | TASK-005 reopen, `docs/spec.md` serializable tx |
| DEC-019 | 2026-06-01 | Windows lock uses `msvcrt.locking` (byte-range), not spec-worded `CreateFile` exclusive | No pywin32 dep; same exclusivity vs same-mechanism contenders; in-bounds sentinel byte before lock | TASK-005 reopen, `docs/spec.md` § startup step 1 |
| DEC-020 | 2026-06-01 | State store v1: single-writer + `BEGIN IMMEDIATE`; revocation durable in SQLite before ledger append | Matches spec single-process constraint; Task 10 chains revocations; `foreign_keys=ON` at open | TASK-006, `docs/plan.md` Task 6 |
| DEC-021 | 2026-06-01 | `open_state_store` rejects incompatible `schema_meta.schema_version`; duplicate idempotency insert fails | Migrations deferred; duplicate key registration is fail-not-idempotent | TASK-006 verification fix pass |
| DEC-022 | 2026-06-01 | Stamp outbox additive table via `init_stamp_outbox_schema`; per-conn cache with table-exists validation | No schema_version bump; cache invalidates on recycled `id(conn)` | TASK-007 reopen |
| DEC-023 | 2026-06-01 | `processing_attempt_identity` on stamp outbox row is the first writer; not updated on cross-attempt recovery | `stamp_id` excludes attempt; row records who opened pending | TASK-007 reopen |
| DEC-024 | 2026-06-01 | Health alert outbox uses separate delivery-attempts table keyed by `(alert_id, channel)` | Future SIEM/chat channels add rows without schema migration | TASK-008, `docs/spec.md` § SystemHealthAlert Delivery |
| DEC-025 | 2026-06-01 | Lazy outbox schema imports in `open_state_store` | Avoids circular import via `state.__init__` when importing outbox modules directly | TASK-008 |
| DEC-026 | 2026-06-01 | `SystemHealthAlert` contract is emission payload only; delivery tracking in SQLite outbox tables | Spec § SystemHealthAlert Delivery separates payload from per-channel delivery status. Structured context for downstream alert codes (e.g. `revocation_feed_unhealthy` emitter in Task 9+) requires a `schema_version` bump per `docs/contracts.md` §15 — not a free additive field. | TASK-008 reopen |
| DEC-027 | 2026-06-01 | Duplicate `alert_id` persist idempotent when payload matches; `DuplicateHealthAlertError` on payload conflict | Safe retry after ambiguous persist exception | TASK-008 reopen |
| DEC-028 | 2026-06-08 | Transaction ownership: gate = pure evaluator, engine = single serializable emit transaction | Keeps PolicyGate on the judgment/authority boundary (no ledger-chain mechanics in the gate); `NeverContainSnapshotRecord` and the edict's `live_never_contain_hash` must commit in one transaction or they can disagree across a crash (`spec.md` § DecisionEdict / snapshot pairing); splitting them is the directive-without-audit-record contradictory-state window | TASK-017 follow-on wiring |
| DEC-029 | 2026-06-09 | Rate-limit ceiling = 1 event per configured scope per `containment_circuit_breaker_policy.window_seconds` | Org config `rate_limit_policy` lists scopes only (no numeric ceilings in schema); Task 17 fixed limit preserved with Task 18 sliding windows | TASK-018 |
| DEC-030 | 2026-06-09 | v1 `per_asset_group` rate scope = host's own `asset_id` only | Real multi-host asset-group membership deferred (`docs/plan.md` deferred work); scope key differs from `per_host` but membership does not span hosts | TASK-018 follow-up |
| DEC-031 | 2026-06-09 | Containment breaker recovers via window elapse on open-check | `is_containment_breaker_open` advances `_advance_breaker_window`; successes cannot recover while open because auto_contain is blocked; matches spec § Circuit Breakers recovery intent | TASK-018 follow-up |
| DEC-032 | 2026-06-11 | Half-open auto-entry timer reuses `provider_health_circuit_breaker_policy.window_seconds` | Org config has no separate probe-timer field; elapsed time since `opened_at` gates timer-based half-open entry | TASK-019 |
| DEC-033 | 2026-06-11 | Probe failure resets `opened_at` to restart half-open cooldown | Prevents immediate timer re-entry after failed probe when original open predates `window_seconds`; breaker returns fully open until cooldown elapses | TASK-019 gatekeeper |
| DEC-034 | 2026-06-11 | Manual revocation via `containment.revocation.manual_revoke_directive` appends `DirectiveRevocationRecord` to hash chain and marks directive revoked in the same `critical_transaction` as feed row + key clear | Feed is a projection of ledger-committed records (`spec.md` § RevocationFeed v1, § DirectiveRevocationRecord); `StateStore.write_manual_revocation` alone remains record+feed+key only for Task-6 store tests | TASK-020 gatekeeper |
| DEC-035 | 2026-06-11 | v1 emitted directives embed an empty `embedded_never_contain_entries` subset when the target has no exact-match never-contain entry at emission | PolicyGate blocks `auto_contain` on live never-contain match before build; exact-match relevance (`embedded_entries_for_target`) yields empty for typical walking-skeleton hosts — Task 21 consumer verifier must not assume non-empty embedded entries | TASK-020 gatekeeper |

Add rows here when implementation choices diverge from or refine docs (with date and evidence).
