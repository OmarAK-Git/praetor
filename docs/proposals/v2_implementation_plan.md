# Praetor V2 Implementation Plan

**Status:** DRAFT - proposed build plan for the V2 backlog.

**Inputs:** `docs/proposals/delivery_backlog.md`, `docs/proposals/v2_hardening.md`,
`docs/plan.md`, `docs/decisions.md`, `memory-bank/`, and selected `.workflow/`
artifacts through TASK-035.

**Purpose:** Convert the delivery backlog into an executable V2 plan with task
ordering, sprint groupings, dependencies, verification gates, and handoff-ready
implementation boundaries. This document does not modify the frozen v1 spec.

## Build Order

Close silent safety inversions first: malformed containment policy schema,
ambiguous authorization posture, host evidence sufficiency, and intake fault
mapping. Then harden the shared guardrails that make future changes auditable:
Outcome Matrix coverage, production state invariants, ledger/feed integrity, and
correlator isolation. After those foundations are stable, add V2 authorization
primitives, account-containment enablement, configurable rate limits, and
production metrics/reporting. Only then build operator-visible V2 features:
progressive authorization reporting, similar-case exemplars, and statute
curation. Roadmap-scale features stay deferred until their contracts are written.

## Governing Constraints

- `docs/contracts.md` remains the source of truth for hashes, ID preimages,
  generated schemas, and Outcome Matrix fault flags.
- Any new hash or serialization contract must update docs before code and add
  exact test vectors.
- Intake must preserve DEC-053: `evaluate_policy_gate(..., persist_directive=False)`
  followed by one engine `critical_transaction` for deferred directive persistence,
  edict append, never-contain snapshot append, and attempt finalization.
- PolicyGate target selection must use the gate's resolved target, not re-derive
  from the raw correlated bundle.
- Recovery paths must not emit new auto-containment unless an explicit owner
  decision supersedes the v1 recovery safety rule.
- Proposed org-config sweep artifacts must remain non-activatable unless promoted
  through an explicit SOC-led workflow.
- Tests that require real providers or live Splunk stay marker-gated and documented;
  local fixture-backed tests must run in the default suite.

## Sprint Groupings

- **Sprint V2-0: Decision and Contract Ratification.** Tasks V2-001 to V2-004.
  Ratify authorization posture, expired-directive supersession semantics,
  never-contain snapshot placement, host corroboration contract, and provider
  unavailable Outcome Matrix behavior.
- **Sprint V2-1: Safety-Critical V1 Gap Closure.** Tasks V2-005 to V2-010.
  Strict containment-rule schema, no silent scope drop, escalate blocks
  containment, provider unavailable handling, compound fault preservation, and
  emergency/never-contain gate alignment.
- **Sprint V2-2: Authorization Rewire Foundations.** Tasks V2-011 to V2-016.
  Host corroboration floor, default-action primitive, default-deny/configurable
  posture, correlator host isolation, gate target ownership, and static guardrails.
- **Sprint V2-3: State, Ledger, Feed, and Metrics Hardening.** Tasks V2-017 to
  V2-023. Production table initialization checks, orphan directive reconciliation,
  revocation/feed supersession clarity, tip-anchor docs/hooks, feed floor
  reconciliation, metrics wiring, and DecisionEdict validators.
- **Sprint V2-4: Feature Enablers and Operator Readiness.** Tasks V2-024 to
  V2-031. Account-containment enablement, all containment through PolicyGate,
  org-config rate ceilings, sweep CLI, provider implementation, Splunk demo
  durability, detection/tooling pins, and benchmark/runbook polish.
- **Sprint V2-5: V2 Product Features.** Tasks V2-032 to V2-036. Progressive
  authorization reporting, prompt exemplar slot, similar-case retrieval, statute
  curation workflow, and eval-regression locking discipline.

## Task V2-001 - Authorization Posture Decision

Complexity: M | Depends on: none

Decision first:

- Ratify whether V2 posture is hard default-deny or deployment-configurable
  `default_action`.
- Define exact `allow`, `deny`, `escalate`, and `auto_contain` semantics,
  including whether a matching `escalate` rule blocks containment.
- Record whether default-allow is formally retired as drift.

Files: `docs/decisions.md`, `docs/proposals/v2_hardening.md`,
`docs/proposals/delivery_backlog.md`.

Done when: one owner decision governs default posture, rule precedence, and
escalate semantics; later schema/policy tasks can implement without open
semantic questions.

## Task V2-002 - Host Corroboration Contract

Complexity: M | Depends on: none

Decision first:

- Promote corroboration from account-only behavior to a host + account
  authorization concept.
- Ratify `insufficient_corroboration` as a policy/safety fault flag with
  `system_fault_escalation=false`.
- Define attacker-controllable provenance classifications for current Windows
  sources and the default for future normalizers.

Files: `docs/contracts.md`, `docs/decisions.md`, `docs/proposals/v2_hardening.md`.

Done when: Outcome Matrix wording and provenance/corroboration semantics are
documented before PolicyGate code changes.

## Task V2-003 - Revocation and Snapshot Owner Decisions

Complexity: M | Depends on: none

Decision first:

- REVIEW-007: decide `NeverContainSnapshotRecord` placement; preferred option is
  paired atomically with edict append.
- REVIEW-008: decide whether expired-directive re-issue creates a
  `DirectiveRevocationRecord` or keeps the current contracts section 4.2
  carve-out.
- Decide startup behavior for expired-unrevoked rows and orphan outstanding
  directives whose ledger edict is missing.

Files: `docs/decisions.md`, `docs/contracts.md`, `src/praetor/engine/edict.py`,
`src/praetor/containment/lifecycle.py`, `src/praetor/policy/state.py`.

Done when: ledger/revocation tasks have a single authoritative semantic target.

## Task V2-004 - Provider Unavailable Outcome Matrix Row

Complexity: S | Depends on: none

Test first:

- Outcome Matrix includes `provider_unavailable` or an owner-approved mapping to
  an existing provider fault flag.
- Enum, metrics, and harness completeness tests reject drift.
- Provider-health breaker behavior remains independent from final edict mapping.

Files: `docs/contracts.md`, `evals/outcome_matrix.py`,
`src/praetor/metrics/events.py`, `tests/evals/`.

Done when: intake can catch `ProviderUnavailableError` without inventing a
runtime-only fault string.

## Task V2-005 - Strict ContainmentRule Schema and Scope Preflight

Complexity: L | Depends on: V2-001

Test first:

- `scope: global` string on a rule fails preflight with a clear code.
- Unknown rule keys fail validation for `ContainmentRule` and
  `ContainmentPolicy`.
- Valid target, asset, and approved catch-all scopes round-trip through
  `OrgConfigSnapshot`.
- Existing example config is updated to a valid shape.

Files: `src/praetor/contracts/org_config_sections.py`,
`src/praetor/config/preflight.py`, `configs/example_org.yaml`,
`tests/config/test_org_config_loader.py`, `tests/config/test_config_gate.py`.

Done when: no declared containment rule can be silently skipped because of an
untyped or malformed `scope`.

## Task V2-006 - Escalate Rule Blocks Containment

Complexity: M | Depends on: V2-001, V2-005

Test first:

- A target matched only by `action: escalate` cannot reach `auto_contain`.
- `deny` and `escalate` produce distinct documented policy results if the owner
  decision requires that distinction.
- `auto_contain` plus unresolved `escalate`/`deny` conflict still produces
  `policy_ambiguity`.

Files: `src/praetor/policy/containment_policy.py`,
`src/praetor/policy/gate.py`, `tests/policy/test_containment_policy.py`,
`tests/policy/test_policy_gate.py`.

Done when: cautious operator rules cannot be treated as allow-by-omission.

## Task V2-007 - ProviderUnavailable Intake Handling

Complexity: M | Depends on: V2-004

Test first:

- `process_alert_intake` catches `ProviderUnavailableError`.
- Final edict matches the documented Outcome Matrix row and sets the expected
  `system_fault_escalation` value.
- Provider-health breaker failure recording remains covered.
- Metrics record only approved LLM/provider fault flags.

Files: `src/praetor/engine/orchestrator.py`, `src/praetor/judgment/provider.py`,
`src/praetor/judgment/provider_health_breaker.py`, `tests/engine/`,
`tests/judgment/`, `tests/metrics/`.

Done when: provider unavailability has a documented, tested intake disposition.

## Task V2-008 - Compound Fault Flag Preservation

Complexity: M | Depends on: none

Test first:

- Stamp `FAILED` plus deferred directive persist conflict preserves both
  `ticket_stamp_failed` and the conflict fault flag.
- Fail-closed final disposition and directive suppression are unchanged.
- Recovery and normal stamp-failed cases continue to match PE-0021/PE-0025.

Files: `src/praetor/engine/orchestrator.py`,
`src/praetor/tickets/contract.py`, `tests/engine/test_intake_stamp_actuation.py`,
`tests/tickets/test_stamp_sequencing.py`.

Done when: DEC-053 audit-flag fidelity is pinned in tests.

## Task V2-009 - Emergency Never-Contain Gate Alignment

Complexity: M | Depends on: V2-003

Test first:

- Active emergency entries block `auto_contain` at the documented layer.
- Activation/emergency/recovery revocation paths share one ledger append policy
  or explicitly document why they differ.
- A harness or integration scenario covers emergency conflict on the intake path.

Files: `src/praetor/policy/gate.py`, `src/praetor/config/emergency.py`,
`src/praetor/config/activation.py`, `src/praetor/engine/recovery.py`,
`tests/policy/`, `tests/config/`, `tests/engine/`.

Done when: emergency never-contain is not only a revocation/recovery concern; it
is visibly part of containment authorization.

## Task V2-010 - Recovery Policy Pinning

Complexity: M | Depends on: V2-003

Test first:

- Recovery downgrade of `auto_contain` is either retained with explicit tests or
  replaced by a documented PolicyGate re-evaluation path.
- Orphan outstanding directives without matching ledger edicts are reconciled,
  purged, or surfaced as a health/audit condition per owner decision.
- Startup step ordering remains singleton lock, SQLite guard, state open,
  engine recovery, feed recovery, intake.

Files: `src/praetor/engine/recovery.py`, `src/praetor/policy/state.py`,
`src/praetor/state/store.py`, `docs/contracts.md`, `docs/operator_runbook.md`,
`tests/engine/`, `tests/policy/`.

Done when: recovery behavior is deliberate, tested, and no longer a soft
accepted-deferral ambiguity.

## Task V2-011 - Host Auto-Contain Corroboration Floor

Complexity: L | Depends on: V2-002

Test first:

- Host `auto_contain` with one cited provenance escalates
  `insufficient_corroboration`.
- Host citations spanning two distinct approved provenance paths pass only when
  at least one source is classified non-attacker-controllable.
- A sole cited `ambiguity_flag=true` fact cannot authorize host containment.
- Existing account corroboration behavior is unchanged.
- Harness scenario covers the new fault flag.

Files: `src/praetor/policy/gate.py`,
`src/praetor/policy/containment_policy.py`, `src/praetor/evidence/provenance.py`,
`src/praetor/evidence/citations.py`, `evals/outcome_matrix.py`,
`evals/scenarios/`, `tests/policy/`, `tests/evidence/`.

Done when: citation metadata resolved by the validator participates in host
authorization, not only target selection.

## Task V2-012 - Default Action Primitive

Complexity: L | Depends on: V2-001, V2-005, V2-006

Test first:

- Org config accepts a typed `default_action` or owner-approved catch-all rule.
- Rule-specific matches override the default with documented precedence.
- Operators can express "escalate by default, allow these groups" in one place.
- Invalid default actions fail preflight.

Files: `src/praetor/contracts/org_config_sections.py`,
`src/praetor/config/preflight.py`,
`src/praetor/policy/containment_policy.py`, `configs/example_org.yaml`,
`tests/config/`, `tests/policy/`.

Done when: default posture is expressible without relying on malformed or
implicit rule fallthrough.

## Task V2-013 - Default-Deny or Configurable Posture Flip

Complexity: L | Depends on: V2-012

Test first:

- No matching rule/default causes host containment to escalate, not allow.
- `confirmed_malicious_sequence` and walkthrough/demo paths are updated with
  explicit allow configuration.
- Example config demonstrates intended allowlist posture.
- Notebook or walkthrough CI checks no longer depend on default allow.

Files: `src/praetor/policy/containment_policy.py`,
`src/praetor/policy/gate.py`, `configs/example_org.yaml`, `evals/scenarios/`,
`docs/operator_runbook.md`, walkthrough/notebook files if present,
`tests/policy/`, `tests/evals/`.

Done when: containment authority is earned by configuration, not granted by
omission.

## Task V2-014 - Correlator Host Isolation

Complexity: L | Depends on: V2-011

Test first:

- Strict xfail for cross-host in-window noise becomes a passing test or is
  replaced by an owner-approved documented gate-only defense.
- Correlation accuracy scenarios distinguish out-of-window exclusion from
  in-window incidental noise.
- Citation-anchored target tests continue to pass.

Files: `src/praetor/correlation/`, `evals/correlation_expected/`,
`tests/correlation/`, `tests/evals/test_phase3_regression_gate.py`,
`tests/policy/test_citation_anchored_host_targeting.py`.

Done when: the correlator no longer relies solely on PolicyGate to compensate
for cross-host bundle collection.

## Task V2-015 - Gate Target Ownership Guard

Complexity: M | Depends on: V2-011

Test first:

- Intake persists only the target returned by PolicyGate evaluation.
- Static or integration guard fails if orchestrator re-derives directive target
  from raw bundle facts.
- Multi-host noise scenario proves uncited hosts cannot affect directive target.

Files: `src/praetor/engine/orchestrator.py`, `src/praetor/policy/gate.py`,
`tests/engine/`, `tests/policy/`.

Done when: AG-0080 is enforced by tests, not only by convention.

## Task V2-016 - Static Policy Fault-Flag Guard

Complexity: M | Depends on: V2-004, V2-011

Test first:

- Policy/engine literal fault flags are a subset of `OutcomeMatrixFaultFlag`.
- `DecisionEdict` construction rejects invalid fault flag/system-fault polarity.
- Harness completeness guard covers newly added flags.

Files: `evals/outcome_matrix.py`, `src/praetor/contracts/`,
`src/praetor/engine/edict.py`, `tests/contracts/`, `tests/policy/`,
`tests/evals/`.

Done when: fault-flag drift cannot enter production code silently.

## Task V2-017 - Production State Initialization Guard

Complexity: M | Depends on: none

Test first:

- `open_production_state_store` under a held singleton creates/asserts all
  required policy tables without manual `init_*` calls.
- Older additive DB fixtures get new tables through `CREATE TABLE IF NOT EXISTS`
  initialization where allowed.
- Incompatible schema version still rejects startup.

Files: `src/praetor/state/store.py`, `src/praetor/runtime/startup.py`,
`src/praetor/policy/state.py`, `tests/`.

Done when: production startup owns table initialization invariants end to end.

## Task V2-018 - Revocation Supersession and Feed Verifiability

Complexity: L | Depends on: V2-003

Test first:

- Expired directive re-issue behavior matches the owner decision.
- Expired-unrevoked outstanding rows do not create duplicate-suppression
  ambiguity.
- Feed records expose enough information for consumers to verify supersession
  chains, or the limitation is explicitly documented as consumer-local.

Files: `src/praetor/containment/lifecycle.py`,
`src/praetor/containment/revocation.py`, `src/praetor/config/state.py`,
`src/praetor/revocation/exporter.py`, `consumer_sdk/reference_verifier.py`,
`docs/contracts.md`, `tests/containment/`, `tests/consumer_sdk/`.

Done when: supersession, expiry, feed projection, and consumer verification are
consistent.

## Task V2-019 - Ledger Tip Anchor and Feed Floor Hardening

Complexity: L | Depends on: V2-017

Test first:

- Runbook documents tail-truncation limitation and an out-of-band tip-anchor
  procedure.
- Optional verifier hook compares current ledger tip against an operator-supplied
  anchor.
- Feed exporter reconciles metadata floor against the on-disk JSONL artifact and
  marks stale metadata unhealthy.

Files: `src/praetor/ledger/`, `src/praetor/revocation/exporter.py`,
`docs/contracts.md`, `docs/operator_runbook.md`, `tests/ledger/`,
`tests/revocation/`.

Done when: known ledger/feed integrity limits are either guarded in code or
operator-visible with tests.

## Task V2-020 - Metrics Production Completeness

Complexity: L | Depends on: V2-007, V2-016

Test first:

- Feed export lag is recorded on export completion, not guessed at intake.
- `record_llm_failure` production call sites pass only `LLM_FAILURE_FAULT_FLAGS`.
- MetricsCollector thread-safety is either documented as single-writer or guarded
  with locking and a concurrency test.
- `engine_intake` eval optionally asserts rate-counter side effects.

Files: `src/praetor/metrics/`, `src/praetor/engine/orchestrator.py`,
`src/praetor/revocation/exporter.py`, `evals/harness.py`, `evals/scenarios/`,
`docs/operator_runbook.md`, `tests/metrics/`, `tests/evals/`.

Done when: live metrics reflect completed production events and cannot record
invalid provider fault strings.

## Task V2-021 - Evidence ID Contract Pin

Complexity: M | Depends on: none

Test first:

- `docs/contracts.md` defines `evidence_id` preimage, domain constant, and input
  ordering.
- Exact test vector pins one known `evidence_id`.
- Domain literal isolation check still passes.

Files: `docs/contracts.md`, `src/praetor/hashing/domains.py`,
`src/praetor/correlation/ids.py`, `tests/hashing/`, `tests/correlation/`.

Done when: DEC-051 is no longer an open doc decision.

## Task V2-022 - SID and Normalizer Conformance

Complexity: M | Depends on: V2-011

Test first:

- SID format validation has pass/fail vectors or a documented v1 waiver.
- Future Windows normalizer test helpers require malformed domain-separator
  accounts to set `ambiguity_flag=true`.
- Existing Sysmon and Security behavior stays pinned.

Files: `src/praetor/policy/identity.py`, `src/praetor/correlation/`,
`tests/evidence/`, `tests/correlation/`.

Done when: account identity confidence does not depend on arbitrary non-empty
SID strings or per-normalizer convention.

## Task V2-023 - Contract Scope Guard and Generated Artifact Hygiene

Complexity: S | Depends on: V2-005, V2-016, V2-021

Test first:

- Scope guard allowlist covers sanctioned V2 docs and source packages only.
- Generated schema artifacts remain deterministic after schema changes.
- Any generator touched by V2 exposes `--check` and `--write` where applicable.

Files: `tests/contracts/test_scope_guard.py`, `schemas/`, generator tools,
`docs/`.

Done when: V2 code/docs do not loosen the repo's contract drift controls.

## Task V2-024 - Account Containment Production Enablement

Complexity: L | Depends on: V2-011, V2-016, V2-022

Test first:

- `account_auto_contain_enabled=true` passes preflight only when identity gates
  are satisfied by local deterministic tests.
- Production account `auto_contain` harness scenario passes with SID-backed,
  corroborated identity.
- Feature-disabled configs still escalate `account_containment_disabled`.

Files: `src/praetor/config/preflight.py`, `src/praetor/policy/gate.py`,
`evals/`, `tests/config/`, `tests/policy/`, `tests/correlation/`.

Done when: account containment can be deliberately enabled without bypassing
Phase 3 identity guarantees.

## Task V2-025 - All Containment Through PolicyGate

Complexity: M | Depends on: V2-024

Test first:

- No production caller authorizes account or host containment by calling lower
  eligibility helpers directly.
- Static grep/AST guard catches direct calls to
  `evaluate_account_containment_eligibility` outside approved tests/policy code.
- Integration tests prove the feature gate cannot be bypassed.

Files: `src/praetor/policy/identity.py`, `src/praetor/policy/gate.py`,
`tests/contracts/`, `tests/policy/`.

Done when: PolicyGate is the single production authorization boundary.

## Task V2-026 - Org-Config Numeric Rate Ceilings

Complexity: L | Depends on: V2-012

Test first:

- Org config declares numeric per-scope ceilings with strict integer validation.
- Gate enforces configured ceilings for host, subnet, and asset-group scopes.
- Missing or invalid ceilings fail preflight, or documented defaults are applied
  consistently.

Files: `src/praetor/contracts/org_config_sections.py`,
`src/praetor/config/preflight.py`, `src/praetor/policy/rate_limit.py`,
`tests/config/`, `tests/policy/test_rate_limits.py`.

Done when: DEC-029's fixed ceiling is replaced or explicitly preserved by
configurable V2 semantics.

## Task V2-027 - Org-Config Sweep CLI

Complexity: M | Depends on: none

Test first:

- CLI runs sweep, writes proposed YAML and markdown report, and exits non-zero on
  invalid inputs.
- Proposed artifacts still fail activation preflight.
- CLI docs state sweep does not infer never-contain, subnet membership, or
  containment policy.

Files: `src/praetor/codification/`, CLI entry point, `docs/operator_runbook.md`,
`tests/codification/`.

Done when: SOC leads have a documented command path for the existing sweep API.

## Task V2-028 - Real Vertex Provider Implementation

Complexity: L | Depends on: V2-007

Test first:

- Vertex/Gemini provider implements the existing Protocol.
- Synthetic canary probe is supported and rate-limited by provider-health breaker.
- Network tests are marker-gated; default suite uses fakes/mocks.
- Unavailable, timeout, malformed response, and refusal map to documented faults.

Files: `src/praetor/judgment/vertex_provider.py`,
`src/praetor/judgment/provider.py`, `tests/judgment/`, `evals/real_provider_adversarial.py`,
`docs/eval_gates.md`.

Done when: a real provider can be used without weakening deterministic CI.

## Task V2-029 - Detection and Splunk Demo Durability

Complexity: M | Depends on: none

Test first:

- Sigma matcher set equals SPL matcher set per rule over manifest fixtures.
- Splunk saved searches use a fixture-stable time window or docs require an
  explicit time-range override.
- Live Splunk Free demo test is env-gated and executable when HEC settings exist.
- `tools/` is either in the mypy gate or its exclusion is documented.

Files: `tests/splunk/`, `tests/detections/`, `tools/spl_match.py`,
`tools/compile_sigma.py`, `splunk/savedsearches.conf`, `splunk/README.md`,
`docs/eval_gates.md`, `pyproject.toml`.

Done when: Phase 4's pass-with-conditions items are closed or deliberately
waived with tests/docs.

## Task V2-030 - Benchmark Burst Measurement and Runbook Pins

Complexity: M | Depends on: V2-020

Test first:

- Burst rate is measured in a separate window or reported with an explicit
  `burst_separately_measured=False` flag.
- Hardware/context metadata is always emitted with benchmark results.
- Operator docs numerical claims are pinned by doc tests.

Files: `benchmarks/serialized_path.py`, `tests/benchmarks/`,
`docs/operator_runbook.md`, `tests/docs/test_docs.py`.

Done when: benchmark outputs cannot be mistaken for unqualified production SLAs.

## Task V2-031 - Consumer Policy and Feed Roadmap Boundary

Complexity: M | Depends on: V2-018, V2-019

Test first:

- Reference verifier documents local consumer policy ownership for contracts
  section 10.6.
- JSONL append-only, no rotation, no feed registry, and no multi-feed directives
  are either preserved as V2 boundaries or promoted to explicit roadmap tasks.
- Consumer residual risk appears in operator docs.

Files: `consumer_sdk/reference_verifier.py`, `docs/contracts.md`,
`docs/operator_runbook.md`, `docs/proposals/delivery_backlog.md`,
`tests/consumer_sdk/`, `tests/docs/`.

Done when: consumer fail-closed responsibilities are clear without pretending V2
ships feed segmentation.

## Task V2-032 - Progressive Authorization Reporting

Complexity: L | Depends on: V2-020, V2-026

Test first:

- Reporting view aggregates PolicyGate override rate and analyst annotation
  outcomes by target type and asset class over a window.
- Reports are read-only decision support; no self-tuning or automatic config
  promotion occurs.
- Runbook documents SOC-led promotion/reversal workflow.

Files: `src/praetor/metrics/`, `src/praetor/annotations/`, reporting module,
`docs/operator_runbook.md`, `tests/metrics/`, `tests/annotations/`.

Done when: SOC leads can make promotion decisions from measured evidence.

## Task V2-033 - Judgment Prompt Exemplar Slot

Complexity: M | Depends on: none

Test first:

- Prompt template accepts an optional exemplar block.
- Exemplar rendering is bounded, auditable, and clearly separated from cited
  evidence.
- Evidence hash and `PromptExcerptSet` behavior are unchanged.

Files: `src/praetor/judgment/prompt.py`, `src/praetor/judgment/excerpt.py`,
`tests/judgment/test_prompt_isolation.py`, `evals/scenarios/`.

Done when: similar-case retrieval has a safe insertion point.

## Task V2-034 - Similar-Case Retrieval

Complexity: L | Depends on: V2-032, V2-033

Test first:

- Retrieval selects only human-confirmed cases that satisfy a documented ranking
  contract.
- Exemplar payloads are bounded and excluded from evidence hash derivation.
- A/B or contract eval proves retrieval is wired without changing citation
  validity or raw-source exclusion.

Files: retrieval module, `src/praetor/judgment/prompt.py`,
`src/praetor/annotations/`, `tests/judgment/`, `tests/annotations/`,
`docs/eval_gates.md`.

Done when: Praetor can use human-reviewed precedent in context without
self-training or mutating authority.

## Task V2-035 - Statute Curation Workflow

Complexity: L | Depends on: V2-027, V2-032

Test first:

- Annotation-to-proposed-statute artifact is review-only and not activatable.
- SOC-lead promotion runs full preflight and records activation audit trail.
- Workflow artifact captures source annotations, proposed edits, reviewer, and
  activation result.

Files: `.workflow/`, `src/praetor/codification/`,
`src/praetor/config/activation.py`, `docs/operator_runbook.md`,
`tests/codification/`, `tests/config/`.

Done when: feedback can become statute only through human-reviewed config
promotion.

## Task V2-036 - Eval Regression Locking Discipline

Complexity: M | Depends on: V2-034, V2-035

Test first:

- Workflow template requires every confirmed model error to identify a harness
  scenario or explicit waiver.
- Eval gate docs define minimum scenario quality and expectation-key validation.
- CI catches stale or unknown expectation keys.

Files: `.workflow/_template/`, `evals/`, `docs/eval_gates.md`,
`tests/evals/`.

Done when: the feedback loop produces durable regression evidence, not just
annotations.

## Phase Gates

### V2 Gate 0 - Decisions Ratified

Required tasks: V2-001 to V2-004.

Pass criteria: authorization posture, host corroboration, snapshot/revocation
placement, and provider-unavailable mapping have owner-approved decisions and
contract updates where required.

### V2 Gate 1 - Safety Gap Closure

Required tasks: V2-005 to V2-010.

Pass criteria: malformed policy scope fails activation, `escalate` cannot permit
containment, provider unavailable is mapped at intake, compound fault flags are
preserved, emergency never-contain blocks at the documented layer, and recovery
semantics are pinned.

### V2 Gate 2 - Authorization Rewire

Required tasks: V2-011 to V2-016.

Pass criteria: host containment requires corroborated cited evidence, default
authorization posture is explicit, no-rule targets do not contain by omission,
correlator/gate target responsibilities are enforced, and fault flags cannot
drift outside the Outcome Matrix.

### V2 Gate 3 - Production Hardening

Required tasks: V2-017 to V2-023.

Pass criteria: production startup initializes required tables, revocation/feed
semantics are consumer-verifiable, ledger/feed integrity limits are guarded or
operator-visible, metrics are wired from real completion points, evidence IDs
are contract-pinned, SID/normalizer conformance is tested, and scope/schema
guards remain strict.

### V2 Gate 4 - Feature Enablement

Required tasks: V2-024 to V2-031.

Pass criteria: account containment can be deliberately enabled through preflight,
all production containment authorization flows through PolicyGate, org-config
rate ceilings are implemented or intentionally waived, sweep has an operator
CLI, provider integration is real but deterministic CI remains stable, Splunk
demo conditions are resolved, and benchmark/operator docs are pinned.

### V2 Gate 5 - Feedback and Progressive Authorization

Required tasks: V2-032 to V2-036.

Pass criteria: promotion reporting is read-only and human-led, prompt exemplars
are bounded and outside the evidence hash path, similar-case retrieval uses only
human-confirmed cases, statute curation is review-only until activation, and
confirmed model errors become eval scenarios or documented waivers.

## Deferred Work

- External CTI enrichment.
- Cloud and Linux telemetry.
- Production WORM/external ledger storage and signed records beyond tip anchors.
- Direct SOAR/EDR actuation adapters.
- Analyst UI beyond annotation/reporting storage.
- Real subnet and multi-host asset-group containment with a membership model.
- Provider tokenizer API budget estimation.
- Horizontal scaling with cross-process state-store serialization.
- Revocation feed segment registry, rotation machinery, and consumer cursor
  registration.
- Multi-feed deployments and `revocation_feed_id` on directives.
- HTTP/API binding for write surfaces.
- SIEM/chat/ticket/SOAR delivery channel implementations.
- Multi-host auto-containment; DEC-052 Option C remains blocked until trusted
  relatedness, blast-radius policy, adversarial evals, per-host auditability,
  and staged rollout all exist.
