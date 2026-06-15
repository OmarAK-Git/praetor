# Praetor implementation decisions

Authoritative product contracts remain in `docs/spec.md` and `docs/contracts.md`.
This file records implementation choices that refine or operationalize those docs.

| ID | Date | Decision | Rationale | Evidence |
|---|---|---|---|---|
| DEC-028 | 2026-06-08 | Transaction ownership: gate = pure evaluator, engine = single serializable emit transaction | Keeps PolicyGate on the judgment/authority boundary (no ledger-chain mechanics in the gate); `NeverContainSnapshotRecord` and the edict's `live_never_contain_hash` must commit in one transaction or they can disagree across a crash; splitting them is the directive-without-audit-record contradictory-state window | `docs/spec.md` § DecisionEdict / snapshot pairing; Task 28a wiring |
| DEC-047 | 2026-06-13 | Task 14 structural prompt isolation is deterministic CI evidence; Task 27 real-provider adversarial excerpt probe is probabilistic and non-gating | Structural tests prove `raw_source` exclusion, excerpt bounds, and omission markers via `build_prompt_excerpt_set` before any live model call. The adversarial probe sends instruction-like normalized-field text to a real provider and logs outcomes only — model compliance cannot be asserted deterministically. Default `pytest` excludes `@pytest.mark.integration` and `@pytest.mark.probabilistic`. | `docs/eval_gates.md`, `evals/real_provider_adversarial.py`, `tests/judgment/test_prompt_isolation.py`, `evals/scenarios/prompt_construction_isolation.yaml` |
| DEC-048 | 2026-06-15 | PolicyGate + `MetricsCollector` integration into the production intake path (`process_alert_intake`) is deferred to the Phase 3 correlation-aware orchestrator (Task 28a), not wired into the walking-skeleton orchestrator | Sprint 3 rebuilds the orchestrator to consume correlated `EvidenceBundle`s (Task 28); wiring into the hardcoded-skeleton path (`SKELETON_EVIDENCE_BUNDLE`) would be discarded immediately. Fail-safe meanwhile: the orchestrator hard-downgrades `auto_contain → escalate`, so no ungated containment can occur. Guarded by strict-xfail tripwire tests so the deferral cannot be silently closed; DEC-028 governs the eventual single-emit-transaction wiring | Phase 2 gate verification (tasks 13-27), `tests/engine/test_policygate_integration_tripwire.py`, `docs/plan.md` Task 28a |
| DEC-049 | 2026-06-15 | Correlation normalizers emit `normalized_fields.host_id` and `normalized_fields.domain` to match PolicyGate consumers (`resolve_host_target`, `extract_account_identity`); not `host` / `account_domain` | Producer keys must align with established consumer field names in `containment_policy.py`, `tests/policy/conftest.py`, and synthetic fixtures; seam pinned by `test_correlation_consumers_resolve_fixture_scenario` | `src/praetor/correlation/{sysmon,security_log}.py`, `tests/correlation/test_sysmon_normalization.py` |
| DEC-050 | 2026-06-15 | `correlate_telemetry` skips unsupported EventIDs and returns an empty `EvidenceBundle` when no supported events remain after window/filter; it does not raise or emit `correlation_failure` | Mixed real streams contain unsupported event types; per-event drop preserves supported facts. Empty-bundle → `escalate(correlation_failure)` + `EMPTY_BUNDLE` substitution is the orchestrator's responsibility at Task 28a (`docs/spec.md` correlation-failure row), not the normalizer's | `src/praetor/correlation/__init__.py`, `tests/correlation/test_sysmon_normalization.py::test_correlate_skips_unsupported_sysmon_event_ids` |
| DEC-051 | 2026-06-15 | `DOMAIN_EVIDENCE_ID` lives in `src/praetor/hashing/domains.py` alongside other domain constants; `derive_evidence_id` remains in `correlation/ids.py` | Centralizes hash-domain registry; whether to pin `evidence_id` derivation in `docs/contracts.md` is an open doc decision deferred this phase | `src/praetor/hashing/domains.py`, `src/praetor/correlation/ids.py` |
| DEC-052 | 2026-06-15 | Host containment targeting is citation-anchored; two or more distinct cited hosts escalate `ambiguous_containment_target` | Unrelated in-window noise must not capture isolation target via first-fact scan; account corroboration unchanged | `src/praetor/policy/containment_policy.py`, `src/praetor/policy/gate.py`, `docs/contracts.md` §13, DEC-052 section below |

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
