# Agentic Judgment: design

**Status:** draft, pending user review
**Author:** brainstorming session, 2026-07-30

## Problem

Praetor's authority/intelligence split is sound: an LLM `ModelJudgment` proposes a disposition, `PolicyGate` deterministically decides whether it's authorized. But the *judgment* half is a genAI wrapper, not an agent:

- `JudgmentProvider.generate_judgment(request) -> ModelJudgment` is a single-shot call. No tool use, no multi-turn reasoning.
- The prompt (`build_judgment_prompt_payload_from_excerpt_set`) force-feeds everything up front: evidence excerpts hard-truncated to 200 chars/field (`MAX_PROMPT_EXCERPT_CHARS`), the **entire verbatim org-config render** (`org_config_verbatim`), and up to 3 pre-retrieved similar-case exemplars (400 chars each) — regardless of whether any of it is relevant to this alert.
- The model cannot ask for more context, re-read something at full length, or decide for itself what corroborating evidence to look for. It gets one shot with a fixed, often noisy or truncated bundle.

This spec redesigns the judgment phase into a bounded, tool-using agent while leaving `PolicyGate` as the sole deterministic safety authority — it does not change what the model is *allowed* to do, only how well it can reason about what it's given.

## Goals

- Let the judgment phase actively gather evidence (within a bounded, read-only, auditable tool surface) instead of receiving a fixed dump.
- Replace the whole-file org-config injection with on-demand section lookup.
- Strengthen the evidentiary basis of judgments via structured fact-gathering and a malicious/benign hypothesis debate before final disposition.
- Preserve full audit reconstructability: the ledger must be able to show exactly what the model looked at and why, not just what it cited in the end.
- Preserve the Judgment/PolicyGate authority boundary exactly as it is today — PolicyGate does not become smarter or looser; it gains a richer, more trustworthy set of provenance paths to reason over.

## Non-goals

- Changing PolicyGate's evaluation logic (never-contain, rate/breaker, rule precedence, idempotency) — untouched.
- New external data-source integrations (asset inventory, identity/directory, threat intel). Tool surface for v1 is limited to data Praetor already stores.
- Replacing the single-shot path. It remains the default; this is additive.
- Re-baselining `provisional_alert_rate_targets` throughput numbers for agentic mode (flagged as follow-on work, not designed here).

## Current state (for reference)

- `praetor.judgment.provider.JudgmentProvider` — Protocol: `generate_judgment(request) -> ModelJudgment`, `probe(...)`.
- `praetor.judgment.vertex_provider.VertexProvider` — single `generateContent` REST call, `responseMimeType: json`, no function/tool calling wired up.
- `praetor.judgment.fake_provider.FakeProvider` — deterministic scenario-scoped fake used by the 32-scenario eval harness.
- `praetor.judgment.excerpt` — builds `PromptExcerptSet`/`PromptExemplarBlock` with head-tail truncation and `raw_source` exclusion (DEC-047 isolation guarantee).
- `praetor.evidence.citations.validate_evidence_citations` — structurally re-validates the model's `cited_evidence_refs` against the fixed `EvidenceBundle` it was given; resolves `provenance_path`/`ambiguity_flag` per citation.
- `praetor.policy.{gate,containment_policy}` + `praetor.evidence.provenance` — DEC-059 host corroboration floor: ≥2 distinct `provenance_path`, ≥1 non-attacker-controllable (today only `windows_security_log` qualifies), no sole ambiguous-flagged citation.
- `praetor.retrieval.similar_cases.retrieve_similar_case_exemplars` — wraps `praetor.annotations.precedent.fetch_human_confirmed_precedents`, which queries `ledger_chain` by `decision_id` for human-confirmed precedents.
- Integration point: `process_alert_intake` (`src/praetor/engine/orchestrator.py`) builds the prompt payload, wraps it in a `JudgmentRequest`, and calls `call_provider_with_latency_tracking(judgment_provider, request, ...)`, which calls `judgment_provider.generate_judgment(request)`. This is a plain dependency-injection seam — the orchestrator does not know or care which `JudgmentProvider` implementation it's holding.

## Architecture

A new package, `praetor.judgment.agentic`, implements a `JudgmentProvider`-conformant provider (`AgenticJudgmentProvider`) that runs a three-phase pipeline per `generate_judgment` call and returns a normal `ModelJudgment`. **No changes to `orchestrator.py` or the `JudgmentProvider` Protocol are required** — swapping to agentic mode is purely a matter of which provider instance is constructed and injected at startup.

```
generate_judgment(request)
        │
        ▼
Phase 1 — source fan-out (parallel, bounded per-source)
   ├─ LedgerHistoryTool subagent      (own tool, own budget)
   ├─ OrgConfigSectionTool subagent   (own tool, own budget)
   ├─ SimilarCaseTool subagent        (own tool, own budget)
   └─ WiderTelemetryTool subagent     (own tool, own budget)
        │  (findings appended to SessionEvidenceRegistry, per-source failures degrade gracefully)
        ▼
Phase 2 — hypothesis debate (reasoning-only, no tools, no new budget for exploration)
   ├─ malicious-case subagent  (reads Phase 1 registry)
   └─ benign-case subagent     (reads Phase 1 registry)
        ▼
Phase 3 — lead reconciliation (reasoning-only, protected minimum time allotment
                                independent of Phase 1/2 overrun)
   └─ produces final ModelJudgment
        │
        ▼
   (unchanged) validate_evidence_citations → PolicyGate → stamp → ledger
```

Phase 1 and Phase 2 each have their own hard time/call budgets; Phase 3's budget is not "whatever's left" — it is reserved independently so a slow gathering phase can never crowd out the reasoning phase that actually produces the disposition.

### Why three phases, not one long tool-use loop

A single agent looping until it decides to stop (or runs out of budget) risks spending its whole budget exploring and being forced to answer mid-thought. Splitting gathering (Phase 1, parallelizable, bounded per source) from debate (Phase 2, reasoning only) from reconciliation (Phase 3, protected time) guarantees the model always has real time to synthesize, and lets exploration happen concurrently across sources instead of serially.

## Tools and the session evidence registry

Four read-only tools in v1, each a thin, allow-listed wrapper over data Praetor already stores — not free-form querying:

| Tool | Wraps | Scope constraint |
|---|---|---|
| `LedgerHistoryTool` | New query over `ledger_chain`, modeled on `fetch_human_confirmed_precedents`'s existing `ledger_chain` lookup pattern, but scoped by host/account instead of by confirmed annotation | Only the current alert's own host/account — no pivoting to other targets |
| `OrgConfigSectionTool` | `fetch_verbatim_render_text` / org-config snapshot, sectioned instead of returned whole | Read-only section fetch by name |
| `SimilarCaseTool` | `retrieve_similar_case_exemplars` (existing, unchanged) | Same human-confirmed precedent set as today, agent-queried instead of pre-injected |
| `WiderTelemetryTool` | `praetor.correlation`, wider time window | Same host/account as the alert; window-bounded |

Every tool call and its result is appended to a **session evidence registry** — the agentic-mode analog of `EvidenceBundle`, tagged with `provenance_path` exactly like today's `EvidenceFact`. `raw_source` isolation (DEC-047) extends to all four tools: they return normalized excerpts only, never raw log content, same discipline as `build_prompt_excerpt_set` today.

## Audit trail

The registry is hash-chained the same way `evidence_bundle_hash` pins today's fixed bundle, but incrementally: every tool call, its result, and each phase's output become part of the session's evidentiary record, and that chain is hashed into the edict alongside the existing `evidence_bundle_hash`/`org_config_snapshot_hash`. The ledger can reconstruct not just what was cited, but what was looked at, in what order, and what each phase concluded — full session reconstructability, not just final-state hashing.

This requires a schema addition (new hash domain + ledger field, e.g. `session_trace_hash`) — scoped as part of this project's implementation, documented in `docs/contracts.md` alongside the existing §3b/§9 hash material.

## PolicyGate / corroboration floor extension

`praetor.evidence.provenance`'s trust classification table gains two non-attacker-controllable entries: `ledger_history` and `org_config_section` — Praetor/operator-authored data, not attacker-injectable log content, by the same reasoning DEC-059 already applies to `windows_security_log`. `similar_cases` remains explicitly **non-evidentiary** (illustration only) — `EXEMPLAR_SCOPE_INSTRUCTIONS` semantics are unchanged, and exemplar citations continue to be rejected the same way they are today.

This means the corroboration floor can now be satisfied by host-history + telemetry, not solely by the one existing security-log source — a genuine strengthening. `meets_host_corroboration` / `meets_account_corroboration` **logic is unchanged**; it consumes a richer set of resolved `provenance_path` values from the registry, same interface as today. This needs a new decision record (next available ID, e.g. DEC-064) extending DEC-059's trust table — not superseding it.

`PolicyGate` remains a pure deterministic evaluator throughout. No judgment logic leaks into it; it only gains new provenance-path vocabulary.

## Failure handling

| Failure | Handling |
|---|---|
| One Phase 1 source subagent fails (timeout/refusal/malformed) | That source's registry contribution is marked unavailable; remaining sources proceed; Phase 2/3 continue with partial findings |
| All four Phase 1 source subagents fail | Escalate with new fault flag `agentic_evidence_gathering_failed` (`system_fault_escalation=true`) — new Outcome Matrix row, same pattern as `provider_unavailable` (DEC-061) |
| Phase 2 or Phase 3 provider failure | Maps to existing `provider_timeout` / `provider_refusal` / `provider_malformed_response` / `provider_unavailable` Outcome Matrix rows, tagged with which phase failed for observability |

No "forced judgment on budget exhaustion" case exists in this design — Phase 3 always gets its protected reasoning allotment, so there is no scenario where the model is cut off mid-synthesis with no time to answer coherently.

## Testing strategy

- New `FakeAgenticProvider` implementing the 3-phase protocol deterministically, mirroring `FakeProvider`'s scenario-scoped mode system.
- New eval-harness scenarios (additive to the 32 existing) under agentic mode: full success, per-source degradation, all-sources-fail escalation, Phase 2/3 provider failures, corroboration satisfied via the new `ledger_history`/`org_config_section` trust classes.
- Existing 32 scenarios, `FakeProvider`, and `VertexProvider` are untouched — single-shot mode's determinism guarantee is not affected.
- New structural isolation tests extending the DEC-047 pattern to each tool: `raw_source` never reaches the model via any tool response; `LedgerHistoryTool`/`WiderTelemetryTool` cannot be queried outside the alert's own host/account scope.

## Rollout

Provider selection (`VertexProvider` vs. `AgenticJudgmentProvider` vs. `FakeProvider`) happens at whatever call site constructs the engine/injects `judgment_provider` — a startup/config concern, not an orchestrator branch. This spec does not design that config surface in detail; it only requires that the choice be per-deployment and reversible, consistent with Praetor's existing progressive-authorization pattern (DEC-058).

## Known cost/latency impact

Agentic mode issues up to ~7 LLM calls per alert (4 Phase 1 subagents + 2 Phase 2 + 1 Phase 3) versus 1 today. This is expected and accepted as the cost of better judgment, but `provisional_alert_rate_targets` will need re-baselining for deployments that enable it — tracked as follow-on work, not designed here.

## Open items for the implementation plan (not decided here)

- Exact per-phase call/time budgets (numeric defaults).
- New hash domain and ledger schema fields for `session_trace_hash`.
- Gemini function-calling wire format for `AgenticJudgmentProvider` (the SDK/REST shape for tool declarations and multi-turn tool responses).
- New Outcome Matrix fault flag registration process (`agentic_evidence_gathering_failed`) through `OutcomeMatrixFaultFlag` enum + `evals/outcome_matrix.py` + harness scenario, per the existing completeness contract (AG-0068 pattern noted in DEC-059).
