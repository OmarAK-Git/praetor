# Active Context

## Current focus

**V2 plan initialized** — executable backlog in `docs/proposals/v2_implementation_plan.md` (**36** tasks, **6** sprints). V1 complete (pytest **778** at TASK-035).

**Sprint V2-0 (Decision and Contract Ratification):** V2-001 through V2-004 complete (DEC-058 – DEC-061). **Gate 0 closed.**

**Sprint V2-1 (Safety-Critical V1 Gap Closure):** V2-005 through V2-010 complete. **V2 Gate 1 closed.**

**Sprint V2-2 (Authorization Rewire Foundations):** V2-011 complete. **V2-012** next — default action primitive (Gate 2).

## Build order (V2)

1. Close silent safety inversions (malformed containment schema, authorization posture, host evidence, intake fault mapping).
2. Harden shared guardrails (Outcome Matrix coverage, state invariants, ledger/feed integrity, correlator isolation).
3. Add V2 authorization primitives, account-containment enablement, rate limits, metrics.
4. Build operator-visible features (progressive authorization reporting, exemplars, statute curation).
5. Defer roadmap-scale features until contracts exist.

## Recently changed

- V2-009: PolicyGate live never-contain authorization wired through `emergency.py`; engine-intake harness emergency setup; `emergency_never_contain_intake.yaml` scenario.

## Current blockers

- **V2 Gate 2** — V2-012 default action primitive is next.
- REVIEW-004 correlator cross-host xfail → V2-014.
- Live Splunk HEC demo env-gated → V2-029.

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. V2 plan SSOT: `docs/proposals/v2_implementation_plan.md`; inputs include `docs/proposals/delivery_backlog.md`, `docs/proposals/v2_hardening.md`.
3. V2 does **not** modify the frozen v1 spec; it hardens and extends on documented decisions.
4. Intake: DEC-053 — `evaluate_policy_gate(..., persist_directive=False)` then one `critical_transaction` for directive + edict co-commit.
5. PolicyGate target selection uses gate-resolved target, not raw bundle re-derivation (AG-0080 → V2-015).
6. Recovery must not emit new auto-containment unless explicit owner decision supersedes v1 rule.
7. Proposed org-config sweep artifacts (`artifact_kind: proposed_org_config`) remain non-activatable.
8. New hash/serialization contracts: doc update + exact test vectors before code.
9. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
10. Eval harness: `python -m evals.harness`; Phase 3 gate: `python -m evals.run_phase3_gate`.
11. Host containment (DEC-052): citation-anchored targeting; V2-002 (DEC-059) pins host corroboration floor; V2-011 implements.
12. Operator docs: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md`.
