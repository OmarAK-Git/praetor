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
| DEC-009 | Unknown | Completed-edict key ≠ `decision_id` | Three-tuple dedupes; attempt identity in `decision_id` | `docs/contracts.md` §3, §5 |
| DEC-010 | Unknown | Revocation feed is projection; chain is audit authority | Feed checksum is corruption-only, not tamper evidence | `docs/spec.md`, `docs/contracts.md` §7 |
| DEC-011 | Unknown | `standard_review` replaces `pass` | Terminology alignment across API/schema/persistence | `docs/spec.md` |
| DEC-012 | Unknown | Account `auto_contain` gated until Phase 3 | SID + distinct-provenance corroboration required | `docs/spec.md`, `docs/plan.md` Phase 3 |

Add rows here when implementation choices diverge from or refine docs (with date and evidence).
