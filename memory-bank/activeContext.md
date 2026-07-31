# Active Context

## Current focus

**2026-07-30 � Agentic judgment sprint COMPLETE (queue drained; uncommitted on agentic-judgment worktree)** on worktree .worktrees/agentic-judgment / branch gentic-judgment. Queue loaded; draining.


**2026-07-30 — Reverse-spec RFC remediation COMPLETE.** Plan
`docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md` drained via GSD on branch
`reverse-spec-rfc-remediation`. Six observability/coverage tasks + disposition record shipped;
RFC-001 rejected under DEC-053; feed rotation stays out of scope. Gate evidence:
`.workflow/rfc-remediation-gate/results/verifier-result.md` (pytest **1047**, ruff/mypy clean).

**Standing model instruction (2026-07-30, until revoked):** all gates use
`cursor-grok-4.5-high` / `in_session_grok` — not Opus. Queued in personal Cursor rule +
`.workflow/autopilot-queue.json` defaults + `OPS.md`.

**2026-07-18 — Reverse spec + debt ledger extraction COMPLETE.** Deliverables at repo root:
`AS_BUILT.md` and `DEBT_LEDGER.md`. Live plan: `IMPLEMENTATION_PLAN.md` (status complete).

**V2 COMPLETE** — Gates 0–5 closed; tasks V2-001–039 done. Correctness audit 2026-07-10:
`.workflow/v2-correctness-audit/final-report.md`.

**Follow-ups:** deferred roadmap / Accepted Deferral / Partial rows only; optional Minor notes
from the RFC remediation final review (orchestrator metric-wiring assert, feed warning dedupe).

**Sprint history (all closed):** V2-0 … V2-5 — see `memory-bank/progress.md` and `.workflow/v2-gate-*-exit/`.

## Build order (V2)

1. Close silent safety inversions (malformed containment schema, authorization posture, host evidence, intake fault mapping).
2. Harden shared guardrails (Outcome Matrix coverage, state invariants, ledger/feed integrity, correlator isolation).
3. Add V2 authorization primitives, account-containment enablement, rate limits, metrics.
4. Build operator-visible features (progressive authorization reporting, exemplars, statute curation) — **V2-032–V2-036 done**.
5. Defer roadmap-scale features until contracts exist.

## Recently changed

- V2-036: eval regression locking — workflow template scenario/waiver discipline; expectation-key CI guard; pytest **132** in evals scope.
- V2-035: statute curation workflow — review-only `proposed_statute` artifacts; SOC-lead `promote_statute_curation`; pytest **109** in codification+config scope.
- V2-034: similar-case retrieval — human-confirmed precedents ranked and wired via exemplar block; pytest **76** in judgment+annotations scope.
- V2-033: judgment prompt exemplar slot — bounded `PromptExemplarBlock`; pytest **9** in prompt isolation tests.
- V2-032: progressive authorization reporting — read-only report by target_type/asset_class; pytest **55** in metrics+annotations scope; gate-5 remediation added `_AnnotationBucket` TypedDict + lint fixes.
- Gate 5 remediation: V2-023 allowlist + `reporting`/`retrieval`; V2-032/V2-034/V2-035 lint/type fixes; ruff/mypy clean repo-wide.
- V2-030: benchmark `measurement_context` always emitted; runbook pins 30/60 targets and burst honesty; pytest **25** in benchmarks+docs scope.
- V2-025: PolicyGate containment boundary — AST guard for eligibility helper calls; integration tests prove `account_containment_disabled` cannot be bypassed via direct helper; pytest **128** in contracts+policy scope.
- V2-024: account containment preflight gated on identity compliance subprocess; harness `account_containment_enabled.yaml`; verifier pass; pytest **177** in config+policy+correlation scope.
- V2-023: scope guard allowlist + `tools/schema_export.py --check`/`--write`; pytest **9** in scope-guard tests.
- V2-020: feed export lag on completion; LLM failure flag guard; metrics thread-safety docs; pytest **133** in metrics+evals scope.
- V2-019: ledger tip-anchor hook + feed metadata floor reconciliation; pytest **62** in ledger+revocation scope.
- V2-022: SID format vectors + normalizer conformance helpers; pytest **105** in evidence+correlation scope.
- V2-021: evidence_id contract pin (DEC-051 closed); pytest **57** in hashing+correlation scope (1 retry for docs closure).
- V2-018: DEC-060 revocation supersession + feed verifiability; pytest **53** in containment+consumer_sdk scope.
- V2-017: production policy table ensure/assert on startup; pytest **54** in state/startup scope.
- V2-016: static fault-flag guard — policy/engine literals ⊆ OutcomeMatrixFaultFlag; edict construction validates flags/SFE; pytest **208** in contracts+policy+evals scope.

## Current blockers

- None for Gate 2. **V2 Gate 2 exit closed** (user-approved remediation fixed 40 ruff findings + the `mypy .` duplicate-`conftest` invocation via `[tool.mypy]` config; full gate green). Evidence: `.workflow/v2-gate-2-exit/results/verifier-result-final.md`.
- Live Splunk HEC demo env-gated → V2-029.

## Recently changed (tooling/config)

- `pyproject.toml` `[tool.mypy]`: added `mypy_path="src"`, `explicit_package_bases=true`, and `exclude` for `tests/`, `tools/`, `.workflow/`, `.claude/`, `notebooks/`, `build/`, `awesome-ai-workflow/` so `mypy .` resolves src-layout + per-dir conftest and checks only the configured source packages. Bare `mypy` unchanged.

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
