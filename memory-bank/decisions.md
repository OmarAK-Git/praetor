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

Add rows here when implementation choices diverge from or refine docs (with date and evidence).
