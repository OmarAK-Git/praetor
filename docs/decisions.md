# Praetor implementation decisions

Authoritative product contracts remain in `docs/spec.md` and `docs/contracts.md`.
This file records implementation choices that refine or operationalize those docs.

| ID | Date | Decision | Rationale | Evidence |
|---|---|---|---|---|
| DEC-028 | 2026-06-08 | Transaction ownership: gate = pure evaluator, engine = single serializable emit transaction | Keeps PolicyGate on the judgment/authority boundary (no ledger-chain mechanics in the gate); `NeverContainSnapshotRecord` and the edict's `live_never_contain_hash` must commit in one transaction or they can disagree across a crash; splitting them is the directive-without-audit-record contradictory-state window | `docs/spec.md` § DecisionEdict / snapshot pairing; Task 28a wiring |
| DEC-047 | 2026-06-13 | Task 14 structural prompt isolation is deterministic CI evidence; Task 27 real-provider adversarial excerpt probe is probabilistic and non-gating | Structural tests prove `raw_source` exclusion, excerpt bounds, and omission markerS via `build_prompt_excerpt_set` before any live model call. The adversarial probe sends instruction-like normalized-field text to a real provider and logs outcomes only — model compliance cannot be asserted deterministically. Default `pytest` excludes `@pytest.mark.integration` and `@pytest.mark.probabilistic`. | `docs/eval_gates.md`, `evals/real_provider_adversarial.py`, `tests/judgment/test_prompt_isolation.py`, `evals/scenarios/prompt_construction_isolation.yaml` |
| DEC-048 | 2026-06-15 | PolicyGate + `MetricsCollector` integration into the production intake path (`process_alert_intake`) is deferred to the Phase 3 correlation-aware orchestrator (Task 28a), not wired into the walking-skeleton orchestrator | Sprint 3 rebuilds the orchestrator to consume correlated `EvidenceBundle`s (Task 28); wiring into the hardcoded-skeleton path (`SKELETON_EVIDENCE_BUNDLE`) would be discarded immediately. Fail-safe meanwhile: the orchestrator hard-downgrades `auto_contain → escalate`, so no ungated containment can occur. Guarded by strict-xfail tripwire tests so the deferral cannot be silently closed; DEC-028 governs the eventual single-emit-transaction wiring | Phase 2 gate verification (tasks 13-27), `tests/engine/test_policygate_integration_tripwire.py`, `docs/plan.md` Task 28a |
| DEC-049 | 2026-06-15 | Correlation normalizers emit `normalized_fields.host_id` and `normalized_fields.domain` to match PolicyGate consumers (`resolve_host_target`, `extract_account_identity`); not `host` / `account_domain` | Producer keys must align with established consumer field names in `containment_policy.py`, `tests/policy/conftest.py`, and synthetic fixtures; seam pinned by `test_correlation_consumers_resolve_fixture_scenario` | `src/praetor/correlation/{sysmon,security_log}.py`, `tests/correlation/test_sysmon_normalization.py` |
| DEC-050 | 2026-06-15 | `correlate_telemetry` skips unsupported EventIDs and returns an empty `EvidenceBundle` when no supported events remain after window/filter; it does not raise or emit `correlation_failure` | Mixed real streams contain unsupported event types; per-event drop preserves supported facts. Empty-bundle → `escalate(correlation_failure)` + `EMPTY_BUNDLE` substitution is the orchestrator's responsibility at Task 28a (`docs/spec.md` correlation-failure row), not the normalizer's | `src/praetor/correlation/__init__.py`, `tests/correlation/test_sysmon_normalization.py::test_correlate_skips_unsupported_sysmon_event_ids` |
| DEC-051 | 2026-06-15 | `DOMAIN_EVIDENCE_ID` lives in `src/praetor/hashing/domains.py` alongside other domain constants; `derive_evidence_id` remains in `correlation/ids.py`; preimage, ordering, and test vector pinned in `docs/contracts.md` §3b (V2-021) | Centralizes hash-domain registry; doc decision closed — contracts §3b is authoritative for derivation | `src/praetor/hashing/domains.py`, `src/praetor/correlation/ids.py`, `docs/contracts.md` §3b, `tests/correlation/test_evidence_id.py` |
| DEC-052 | 2026-06-15 | Host containment targeting is citation-anchored; two or more distinct cited hosts escalate `ambiguous_containment_target` | Unrelated in-window noise must not capture isolation target via first-fact scan; account corroboration unchanged | `src/praetor/policy/{containment_policy,gate}.py`, `docs/contracts.md` §13, DEC-052 section below |
| DEC-053 | 2026-06-15 | Intake path: `evaluate_policy_gate(..., persist_directive=False)`; after terminal stamp, directive + idempotency/rate writes + edict + never-contain snapshot commit in one engine `critical_transaction` | Refines DEC-028 for stamp ordering: no exportable directive before edict; prevents in-flight stamp leaving an outstanding directive without ledger record. `DeferredDirectivePersistConflict` suppresses directive and rebuilds escalate edict in-band; compound-fault rebuild re-applies `apply_terminal_stamp_to_disposition` so `ticket_stamp_failed` is preserved alongside the conflict flag | `src/praetor/engine/orchestrator.py:398-507`, `src/praetor/policy/gate.py`, `tests/engine/test_intake_stamp_actuation.py` |
| DEC-054 | 2026-06-16 | Org-config sweep proposed artifacts use `version_metadata.artifact_kind: proposed_org_config` and preflight rejects them with `proposed_artifact_not_activatable`; unreplaced sweep sentinel values (`UNOBSERVED-REQUIRES-HUMAN-REVIEW`, `REPLACE-BEFORE-ACTIVATION`) are rejected with `unreplaced_sweep_placeholder` even when the marker is stripped; zero-evidence sweeps emit `activation_status: unusable_zero_evidence` with empty asset entries that fail activation via Pydantic `min_length` (`invalid_snapshot`) when marker and sentinels are stripped | Marker-only rejection is insufficient — placeholders pass schema validation; fail-closed on sentinels closes activation hole; empty `assets_and_asset_groups.entries` is a defense-in-depth backstop (incidental `invalid_snapshot`, not a dedicated zero-evidence code) | `src/praetor/codification/{models,placeholders,sweep}.py`, `src/praetor/config/preflight.py`, `tests/codification/test_sweep.py::test_zero_evidence_marker_stripped_still_rejected_by_preflight` |
| DEC-055 | 2026-06-16 | **SUPERSEDED BY DEC-056** — Production serialized-path benchmark ran `evaluate_policy_gate` (own `critical_transaction`) then a second transaction for ledger append + automated revocation feed outbox | Superseded when Task 35 gatekeeper realigned the benchmark to DEC-053 deferred-directive persist (no per-alert revocation) | TASK-035; see DEC-056 |
| DEC-056 | 2026-06-16 | Task 35 production benchmark (`benchmarks/serialized_path.py`) mirrors DEC-053: gate eval with `persist_directive=False` (one `BEGIN IMMEDIATE`), then one engine transaction for deferred directive persist + ledger append; no per-alert revocation/feed outbox; default rate is uncontended distinct-host best case; burst target comparison is informational only in v1 | Prior benchmark used `persist_directive=True` plus spurious per-alert revocation, inverting stamp ordering and polluting capacity numbers; smoke benchmark remains the separate revocation throughput measurement; supersedes DEC-055 | `benchmarks/serialized_path.py`, `tests/benchmarks/test_serialized_path.py`, `docs/operator_runbook.md`, DEC-056 |
| DEC-057 | 2026-06-16 | Sweep placeholder activation scan (`collect_sweep_placeholder_violations`) covers only safety-critical fields: `assets_and_asset_groups.entries[].subnet_membership` and `containment_exclusions.never_contain[].target_id`. Advisory placeholder prose in `business_context.notes` and `normal_admin_patterns[].description` is intentionally **not** activation-blocking — SOC review reminders, not containment topology | Subnet and never-contain target IDs directly affect isolation scope; narrative fields are review prompts and do not gate containment decisions | `src/praetor/codification/placeholders.py`, `src/praetor/codification/sweep.py`, `tests/codification/test_sweep.py` |
| DEC-058 | 2026-06-29 | V2 containment authorization posture is **deployment-configurable** via a required `default_action` on `ContainmentPolicy`; v1 implicit default-allow is **retired drift**; sole matching `escalate` rules **block** `auto_contain` | Containment must be earned by explicit configuration, not granted by omission; operators need a catch-all primitive for progressive authorization; `escalate` as hint-only contradicts operator intent (example `default_escalate` + silent scope drop) | V2-001; `docs/proposals/v2_hardening.md` Item 2; implementation in V2-005–V2-006, V2-012–V2-013 |
| DEC-059 | 2026-06-29 | V2 host corroboration floor: cited facts for host `auto_contain` require ≥2 distinct `provenance_path` values with ≥1 non-attacker-controllable; sole `ambiguity_flag=true` cited fact cannot authorize host containment; fault flag `insufficient_corroboration` (`system_fault_escalation=false`); account path unchanged (`ambiguous_target_identity`) | v1 solved citation-anchored targeting (DEC-052) but not evidence sufficiency; extends account corroboration discipline to hosts; raises bar from single forged log line to convergent independent collection paths | V2-002; `docs/contracts.md` §12a/§13; implementation in V2-011 |
| DEC-060 | 2026-06-29 | V2 revocation/snapshot semantics: `NeverContainSnapshotRecord` appended only in engine post-stamp transaction paired with `DecisionEdict` (not in PolicyGate); `snapshot_content` is the gate-supplied full live never-contain list from serializable PolicyGate evaluation (conflict rebuild paths may refresh); expired-directive fresh re-issue retains §4.2 carve-out; expired-unrevoked rows excluded from step-6 idempotency; orphan directives skipped at step 6 and surfaced in V2-010 | Closes REVIEW-007/008 timing ambiguity; ratifies v1 intake behavior; commit-time-only capture is not the v1 contract | V2-003; `docs/contracts.md` §4.2/§7a; V2-003 reopen 2026-06-29 |
| DEC-061 | 2026-06-29 | V2 `provider_unavailable` Outcome Matrix row for `ProviderUnavailableError`: `escalate` with `system_fault_escalation=true`; distinct from `provider_timeout`, `provider_refusal`, and `provider_health_breaker_open`; breaker tripping unchanged | Intake lacked documented fault flag for provider unavailability; closes Gate 0 provider mapping | V2-004; `docs/contracts.md` §13; V2-007 extends intake/metrics tests |
| DEC-064 | 2026-07-30 | Agentic judgment: `ledger_history` added to the DEC-059 non-attacker-controllable provenance set; `org_config_section` and `similar_cases` are explicitly **not** corroboration-eligible (org-config content flows through `ModelJudgment.org_config_refs`, never `cited_evidence_refs`; similar-case exemplars remain illustration-only per existing `EXEMPLAR_SCOPE_INSTRUCTIONS`); new Outcome Matrix row `agentic_evidence_gathering_failed` (`system_fault_escalation=true`) for all-Phase-1-sources-failed | Extends DEC-059's corroboration floor to a genuine second independent observation source (Praetor's own past decisions) without opening a free-corroboration hole via always-available static content; mirrors DEC-061's minimal-orchestrator-catch pattern for the new failure mode | `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md`; `src/praetor/evidence/provenance.py`; `src/praetor/judgment/agentic/`; `src/praetor/metrics/events.py`; `src/praetor/contracts/fault_flags.py` |

Add rows when implementation choices diverge from or refine authoritative docs.

## DEC-052 — Host containment targeting is citation-anchored; multi-host ambiguity escalates

**Status:** accepted (2026-06-15)

**Context.** `resolve_host_target` returned the first fact carrying a `host_id`, scanning the whole `EvidenceBundle`. Because correlation is time-windowed and tolerates bounded noise (DEC for TASK-030 / `otrf_unrelated_in_window_noise`), an unrelated in-window event from a different host (e.g. record 1004 on WORKSTATION2) could be ordering-dependently selected as the isolation target — silently isolating an innocent host. Two constraints: do not blindly pick the first host, and do not escalate merely because a bundle spans >1 host (legitimate incidents and in-window noise both produce that).

**Decision (Option A).** Derive the HOST containment target only from the facts the model **cited** (`judgment.cited_evidence_refs`, already validated at gate time):

- exactly one distinct cited host -> contain it;
- two or more distinct cited hosts -> escalate `ambiguous_containment_target` (`system_fault_escalation = false`, policy/safety-gate class);
- account targeting is unchanged (corroboration legitimately spans the bundle).

Uncited noise (a different host's in-window event that the model did not point at) cannot pollute or capture the target, so the raw host count is no longer inflated by noise — which is why "escalate when >1" becomes correct rather than over-broad.

**Why A over B (connected-subgraph) and C (hybrid connectivity) now:**

1. **Trust.** B/C derive relatedness from `ParentProcessGuid`/`ProcessGuid` in the Sysmon event payload — telemetry content the spec deliberately distrusts for safety-critical decisions (contracts §13 / corroboration requires a fact that is not attacker-controlled log content). Citations reference Praetor-assigned `evidence_id`s that are independently validated (`invalid_model_citation`). Targeting must not rest on spoofable/injectable linkage.
2. **B collapses into A.** "Connected to the anchor" needs a trusted seed; the only trusted seed is the citation. B is A plus graph machinery, not a different foundation.
3. **C bakes an undecided policy.** C exists to auto-contain a *second* host without human review. Multi-machine isolation is exactly what should require approval in v1; A routes it to a human.
4. **Audit surface.** This function decides which machine gets forcibly isolated; small and auditable beats a graph algorithm with ordering/edge-case failure modes.
5. **Safe failure direction.** A's weakness (model under-cites -> contains one host, misses another) fails toward *incomplete* containment, never toward isolating an innocent host; and B/C would "fix" it only by inferring the missing host from the same low-trust edges.

**Conditional requirements to revisit Option C later.** Upgrade from "escalate on >=2 cited hosts" to "evaluate connectivity; contain the related set or escalate if disjoint" only when ALL hold:

- C1. A **tamper-evident, Praetor-assigned** relatedness signal exists (correlation provenance stamped by Praetor with integrity guarantees) — not attacker-emitted process GUIDs.
- C2. An explicit, approved policy that **multi-host auto-containment without human review** is acceptable, with defined blast-radius limits (max hosts per action, asset-group scoping, never-contain interaction).
- C3. Adversarial eval scenarios prove the relatedness signal resists **false-link** (cannot be spoofed into linking an innocent host) and **false-split** (cannot be made to drop a real host).
- C4. Each host in a multi-host action carries its **own cited justification** in the decision ledger (per-host auditability).
- C5. A staged rollout exists (dry-run / proposal-only for multi-host actions) before enforcement.

**Upgrade path.** The `ambiguous_containment_target` escalation branch is the exact hook for C: when C1–C5 hold, that branch changes from "escalate" to "consult the trusted relatedness signal." No other contract changes; the fault flag and Outcome Matrix row remain (escalation becomes the fallback for genuinely disjoint multi-host targets).

**Doc placement.** Outcome Matrix row added to `docs/contracts.md` §13 this phase; the `docs/spec.md` §Outcome Matrix mirror is deferred until spec unfreezes.

## DEC-058 — V2 containment authorization posture and rule-action semantics

**Status:** accepted (2026-06-29, V2-001)

**Context.** v1 `evaluate_target_containment_policy` returns `ALLOW` when no scoped rule matches the target (`containment_policy.py:251`). Combined with silently dropped malformed rule scopes (`scope: global` string), an operator's cautious config can invert to containment-permitted-by-default. Cross-review with the original spec author confirmed this is **drift**, not an intentional denylist posture (`docs/proposals/v2_hardening.md` Item 2). V2 must ratify posture, rule actions, and precedence before schema/policy code changes (V2 Gate 0).

### Posture decision

**Chosen:** deployment-configurable `default_action` on `ContainmentPolicy` — **not** a hard-coded engine denylist.

- Activated org configs **must** declare `default_action` (preflight rejects missing/invalid values — V2-012).
- When **no scoped rule** matches the resolved containment target, the policy layer applies `default_action` (catch-all, **lowest precedence**).
- **Recommended default for new deployments:** `escalate` (progressive authorization: containment earned via explicit allow rules).
- **Retired:** v1 implicit `ALLOW` fallthrough when no rule matches. That behavior is documented as implementation drift to be removed in V2-013; it is not a product decision.

`default_action` permitted values match rule `action` vocabulary: `allow`, `deny`, `escalate`, `auto_contain`.

### Rule `action` semantics (policy authorization layer)

These actions govern whether PolicyGate **may authorize** an `auto_contain` proposal for a target. They do not force containment without a matching model proposal and downstream gates (never-contain, corroboration, rate/breaker, feed health, stamp, etc.).

| Action | Policy-layer effect | Blocks `auto_contain`? |
|---|---|---|
| `allow` | Affirmative authorization for matched scope | No |
| `auto_contain` | Same as `allow` at authorization layer — explicit permit for matched scope | No |
| `deny` | Explicit prohibition for matched scope | **Yes** |
| `escalate` | Operator policy requires human review before containment | **Yes** |

**`escalate` is not hint-only.** A target matched **only** by `action: escalate` (scoped rule or `default_action: escalate`) must **not** reach `auto_contain` at the policy layer (V2-006 implements and tests).

**`deny` vs `escalate` distinction (audit):** both block containment. `deny` means the operator forbids automated containment for the scope; `escalate` means the operator defers containment authority to human review. V2-006 maps these to distinct policy-layer results and Outcome Matrix fault flags (`containment_policy_denied`, `containment_policy_escalation_required` — names provisional until contracts §13 rows land).

### Rule precedence

1. **Scoped rules first** — evaluate all `containment_policy.rules` whose `scope` matches the resolved target (`target_id`, `asset_id`/subnet membership per existing asset-group logic).
2. **Conflict detection** — if matched actions include both permitting (`allow`/`auto_contain`) and blocking (`deny`/`escalate`) actions, apply `containment_policy.precedence` when present; if precedence does not resolve the conflict, emit `policy_ambiguity` (`system_fault_escalation=false`).
3. **Blocking wins among non-conflicting multiples** — if any `deny` matches, result is deny-blocked; else if any `escalate` matches (and no permit), result is escalate-blocked; else if any `allow`/`auto_contain` matches, result is permitted.
4. **Catch-all last** — when no scoped rule matches, apply `default_action` with the same action semantics table above.

### Implementation map (out of V2-001 scope)

| Follow-on | Delivers |
|---|---|
| V2-005 | Typed `scope`, `extra="forbid"`, preflight rejects malformed scope |
| V2-006 | `escalate`/`deny` block containment; distinct policy results; conflict → `policy_ambiguity` |
| V2-012 | `default_action` schema + preflight |
| V2-013 | Remove implicit ALLOW; example config + evals express explicit permits |

**Doc placement.** Contracts Outcome Matrix rows for new deny/escalate fault flags land with V2-006; `docs/spec.md` mirror deferred until spec unfreeze (same pattern as DEC-052).

## DEC-059 — Host corroboration contract and `insufficient_corroboration`

**Status:** accepted (2026-06-29, V2-002)

**Context.** DEC-052 made host containment **target selection** citation-anchored (which host), but a single cited Sysmon fact can still authorize host `auto_contain` today. v1 account containment already requires distinct-provenance corroboration (`spec.md` § Account Containment; `meets_account_corroboration` in `provenance.py`), while hosts received targeting integrity without an evidence-sufficiency floor (`docs/proposals/v2_hardening.md` Item 1). V2 promotes corroboration to a first-class authorization concept for **both** host and account paths.

### Corroboration as first-class authorization

Corroboration governs whether PolicyGate **may authorize** an `auto_contain` proposal — alongside never-contain, policy rules, rate/breaker, feed health, and stamp gates. It is evaluated on **resolved citation metadata** (`provenance_path`, `ambiguity_flag`) from `validate_evidence_citations`, not on raw bundle scans unrelated to the model's citations.

### Host corroboration floor (V2-011 implements)

Before authorizing host `auto_contain` for a citation-anchored host target (DEC-052), cited facts must:

1. span **≥2 distinct** `provenance_path` values;
2. include **≥1** fact from a **non-attacker-controllable** path; and
3. **not** rely on a **sole** cited fact with `ambiguity_flag = true`.

Failure → `escalate(insufficient_corroboration)` with `system_fault_escalation = false` (policy/safety-gate class). Outcome Matrix row in `docs/contracts.md` §13.

### Account path unchanged

Account identity corroboration rules are **unchanged**. SID-backed account targets that fail distinct-provenance corroboration continue to escalate **`ambiguous_target_identity`** (`system_fault_escalation = false`). Host corroboration does not subsume or rename the account identity fault flag.

| Target kind | Corroboration failure | Fault flag |
|---|---|---|
| Account (SID-backed, uncorroborated) | Insufficient distinct provenance for identity | `ambiguous_target_identity` |
| Host (cited-evidence floor) | Insufficient cited provenance / sole ambiguous basis | `insufficient_corroboration` |

### Attacker-controllable provenance classification (v1 Windows)

| `provenance_path` | Classification | Notes |
|---|---|---|
| `sysmon_event_log` | **Attacker-controllable** | Command lines, process metadata, and other injectable event payload content |
| `windows_security_log` | **Non-attacker-controllable** | Independent Security-channel authentication events |

These constants match `src/praetor/evidence/provenance.py` (`SYSMON_EVENT_LOG`, `WINDOWS_SECURITY_LOG`).

### Default for future normalizers

Any new `provenance_path` introduced by a correlation normalizer defaults to **attacker-controllable** until explicitly listed as non-attacker-controllable in `docs/contracts.md` §12a. This fail-closed default prevents a new telemetry source from silently satisfying corroboration without an owner-reviewed trust classification.

### Implementation map (out of V2-002 scope)

| Follow-on | Delivers |
|---|---|
| V2-011 | Gate reads resolved citation `provenance_path` / `ambiguity_flag`; `meets_host_corroboration` helper; `OutcomeMatrixFaultFlag.INSUFFICIENT_CORROBORATION`; harness scenario; policy tests |

**Doc placement.** §12a and §13 row land in V2-002; enum/metrics/harness wiring lands in V2-011 per AG-0068 completeness contract. `docs/spec.md` mirror deferred until spec unfreeze.

## DEC-060 — Revocation, snapshot placement, and startup reconciliation semantics

**Status:** accepted (2026-06-29, V2-003)

**Context.** TASK-017 left REVIEW-007 (where `NeverContainSnapshotRecord` is appended), REVIEW-008 (whether expired-directive re-issue writes a supersession revocation), and startup reconciliation for expired-unrevoked and orphan outstanding directive rows as open owner decisions. v1 code and tests already implement much of the recommended posture; V2-003 ratifies a single semantic target for downstream ledger/revocation tasks.

### NeverContainSnapshotRecord placement (REVIEW-007)

**Decision:** Option 2 — engine edict-append pairing (refines DEC-028 and DEC-053).

- PolicyGate is a **pure evaluator** and must **not** append `NeverContainSnapshotRecord` (or any ledger row).
- The engine appends `NeverContainSnapshotRecord` and `DecisionEdict` in **one** terminal post-stamp `critical_transaction`.
- `DecisionEdict.live_never_contain_hash` must match the snapshot record's `snapshot_content` hash (§9 relationship paragraph).
- **No duplicate snapshot writes** — exactly one snapshot record per qualifying edict commit.

### NeverContainSnapshotRecord `snapshot_content` timing (V2-003 reopen)

**Decision:** Ratify existing v1 intake behavior — **gate-evaluation capture**, not commit-time re-read as the default contract.

On the production intake path (`evaluate_policy_gate(..., persist_directive=False)` → terminal stamp → engine commit):

1. PolicyGate returns `live_never_contain_entries`: the **full** combined permanent + active-emergency list read inside the gate's serializable evaluation transaction (`read_live_never_contain_entries` at in-tx refresh time).
2. The engine uses that gate-supplied tuple as `NeverContainSnapshotRecord.snapshot_content` when building and appending the paired edict + snapshot (empty tuple may fall back to a live read — v1 seam only).
3. **Conflict rebuild paths** (e.g. `DeferredDirectivePersistConflict` between gate evaluation and post-stamp persist) **may refresh** `snapshot_content` via `read_live_never_contain_entries` immediately before rebuilding the edict and appending — the refreshed list is authoritative for that commit.

**Not the v1 contract:** requiring commit-time `read_live_never_contain_entries` on every intake path regardless of gate output. That would be **implementation work** for an owning follow-on task if product intent changes; current code does not generally do that on the happy path.

Recovery and other non-intake edict-append paths read the live list at their own commit site; they are out of V2-003 scope but are not the intake gate-evaluation capture model above.

### Expired-directive fresh re-issue (REVIEW-008)

**Decision:** Retain `docs/contracts.md` §4.2 carve-out (PE-0015). Natural expiry is **not** supersession.

When a directive is past `expires_at` but still `revoked = 0`:

- A fresh emission for the same alert-target-scope may reuse the **same idempotency key**.
- The replacement gets a **new** `directive_id`.
- `supersedes_directive_id` remains **unset** on the replacement (expiry already made the prior directive non-outstanding).
- **No** `DirectiveRevocationRecord` and **no** revocation feed row are written for the expired directive.

**Still-live supersession** (outstanding, unexpired, unrevoked) continues to require a `DirectiveRevocationRecord` with `reason = supersession`, a feed row, and `superseded_by_directive_id` on the revocation record. v1 PolicyGate suppresses re-issue while a directive is live via idempotency, so live supersession remains defined but rarely exercised until later tasks.

### Expired-unrevoked rows at startup

**Decision:** Retain as audit residue; exclude from active reconciliation.

- `outstanding_containment_directives` may contain expired-unrevoked rows (`revoked = 0`, `expires_at <= now`).
- `fetch_outstanding_unrevoked_directives` filters `expires_at > now`, so startup step 6 (`reconcile_policy_state`) does **not** re-register idempotency for expired rows.
- Duplicate suppression and fresh re-issue at PolicyGate use the same non-expired filter — correctness does **not** require purging expired rows.
- Optional archival purge or compaction is deferred to **V2-010** (operator-visible cleanup), not V2-003.

### Orphan outstanding directives (no ledger edict)

**Decision:** Skip idempotency at step 6; surface health condition in V2-010.

An outstanding directive row whose `decision_id` has **no** matching ledger `DecisionEdict` (half-committed directive without edict) is an **orphan**:

- Startup step 6 **must not** re-register its idempotency key (AG-0045; `test_reconcile_skips_idempotency_when_ledger_edict_missing`).
- Orphans **must not** be silently ignored — **V2-010** emits an operator-visible `SystemHealthAlert` (or equivalent audit condition) when orphans exist at startup.
- Engine startup recovery (steps 4/5) remains authoritative for resolving the parent attempt; automatic orphan purge without recovery context is **forbidden**.

### Implementation map (out of V2-003 scope)

| Follow-on | Delivers |
|---|---|
| V2-009 | Emergency never-contain gate alignment; unified ledger-append policy for activation/emergency/recovery revocation paths |
| V2-010 | Recovery pinning; orphan health surfacing; optional expired-row archival |
| V2-018 | Feed supersession verifiability aligned with DEC-060 expired vs live supersession split |

**Doc placement.** §4.2 and §7a pins land in V2-003. `docs/spec.md` mirror deferred until spec unfreeze.

## DEC-061 — Provider unavailable Outcome Matrix row

**Status:** accepted (2026-06-29, V2-004)

**Context.** TASK-019 wired `ProviderUnavailableError` into `provider_failure_trips_breaker`, but intake had no Outcome Matrix row — `process_alert_intake` could not map the exception to a documented fault flag (`docs/proposals/delivery_backlog.md` P1 row). V2 Gate 0 requires provider-unavailable mapping ratified before V2-007 intake hardening.

### Fault flag and disposition

**Decision:** add canonical fault flag **`provider_unavailable`** (not alias to `provider_timeout` or `provider_refusal`).

| Condition | Disposition | Fault flag | system_fault_escalation |
|---|---|---|---|
| Typed `ProviderUnavailableError` before a successful judgment | `escalate` | `provider_unavailable` | `true` |

**Covers:** provider integration not configured for live calls; transport/upstream failures surfaced as `ProviderUnavailableError` (e.g. HTTP 5xx, connection reset); immediate unavailability before bounded-retry timeout exhaustion.

### Distinctions (must not conflate)

| Signal | Fault flag | Notes |
|---|---|---|
| Bounded retry window exhausted without response | `provider_timeout` | PE-0019 / PE-0009 |
| Provider explicitly refused judgment | `provider_refusal` | PE-0009 |
| Provider-health breaker open blocks call | `provider_health_breaker_open` | Breaker gate, not provider exception mapping |
| `ProviderUnavailableError` on production/probe call | `provider_unavailable` | This decision |

### Provider-health breaker independence

`ProviderUnavailableError` **continues** to count as a breaker-tripping production failure (`provider_failure_trips_breaker`). Breaker state transitions and final edict fault flags are **orthogonal**: tripping the breaker does not substitute `provider_health_breaker_open` for `provider_unavailable` on the edict emitted from the unavailable exception path unless the breaker open-check blocks the call first (existing behavior).

### Implementation map

| Follow-on | Delivers |
|---|---|
| V2-007 | Fuller intake tests, metrics `record_llm_failure` production wiring, breaker recording coverage |
| V2-016 | Static guard: policy/engine literals ⊆ `OutcomeMatrixFaultFlag` |
| V2-020 | Metrics production completeness |

**Doc placement.** §13 row lands in V2-004; enum, `evals/outcome_matrix.py`, harness scenario, and minimal orchestrator catch in V2-004. `docs/spec.md` mirror deferred until spec unfreeze.

## DEC-062 — SID identity eligibility remains presence-only (v1 waiver)

**Status:** accepted (2026-07-09, V2-022)

**Context.** Account containment eligibility historically treated any non-empty SID string as SID-backed so synthetic fixtures and early telemetry could flow. Contracts §11 already define a Windows SID form for directive emission; tightening eligibility to that form without a recorded waiver would break fixtures and blur the v1→V2 boundary.

### Decision

- `is_sid_backed` remains **presence-only**: non-empty, non-whitespace SID strings qualify for identity eligibility.
- Strict Windows SID form is exposed via `is_valid_sid_format` (contracts §11 pattern) with pinned pass/fail vectors in `tests/evidence/test_sid_format.py`.
- Format validation **does not yet gate** `is_sid_backed`. Directive emission continues to validate SID form separately where required.
- Future tightening of eligibility to format-valid SIDs requires an explicit follow-on decision (not silently flipped).

**Doc placement.** Recorded here; memory-bank index row retained as pointer. Implementation: `src/praetor/policy/identity.py`.

## DEC-063 — Windows normalizer PE-0024 domain-separator ambiguity

**Status:** accepted (2026-07-09, V2-022)

**Context.** PE-0024 requires that combined account fields lacking a `DOMAIN\\user` separator set `ambiguity_flag=true`. Sysmon and Security normalizers must share one conformance rule so future event-type normalizers cannot drift.

### Decision

- Shared helpers live in `correlation/normalizer_conformance.py` (`require_domain_separator_ambiguity_flag`).
- Sysmon (and other Windows normalizers) call the shared helper; conformance tests pin the rule.
- Future event-type normalizers must use the same helper and add conformance coverage.

**Doc placement.** Recorded here; memory-bank index row retained as pointer.

## DEC-064 — Agentic judgment corroboration extension and evidence-gathering failure row

**Status:** accepted (2026-07-30)

**Context.** Agentic judgment (`praetor.judgment.agentic`) adds bounded tool-using evidence gathering before hypothesis debate and lead reconciliation. Phase 1 can fail per-source (graceful degradation) or all-sources (no findings to debate). DEC-059's corroboration floor needed extension for `ledger_history` without opening free-corroboration via always-available org-config or illustration-only exemplars.

### Corroboration trust extension

**Decision:** add `ledger_history` to the non-attacker-controllable provenance set (DEC-059). Explicitly **exclude** `org_config_section` and `similar_cases` from corroboration eligibility — org-config flows through `ModelJudgment.org_config_refs`; exemplars remain illustration-only per `EXEMPLAR_SCOPE_INSTRUCTIONS`.

### Outcome Matrix row

| Condition | Disposition | Fault flag | system_fault_escalation |
|---|---|---|---|
| All four Phase 1 agentic source subagents fail before judgment | `escalate` | `agentic_evidence_gathering_failed` | `true` |

**Orchestrator mapping:** `AgenticEvidenceGatheringFailedError` → `_finish_system_fault` (not `_finish_provider_fault`). This is a data-layer gathering failure, not LLM provider health — it does **not** trip the provider-health breaker (contrast DEC-061 `provider_unavailable`).

### Session trace hash

Agentic-mode edicts carry optional `DecisionEdict.session_trace_hash`, copied from `ModelJudgment.session_trace_hash` (hash domain `DOMAIN_SESSION_TRACE` / `compute_session_trace_hash` in `docs/contracts.md` agentic-session section).

**Doc placement.** §13 Outcome Matrix row and agentic-session hash domain in `docs/contracts.md`; implementation in `src/praetor/judgment/agentic/`, `src/praetor/engine/orchestrator.py`, `src/praetor/contracts/edict.py`.
