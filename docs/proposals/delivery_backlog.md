# Praetor Delivery Backlog

**Status:** DRAFT — harvested from `docs/proposals/v2_hardening.md`, `docs/plan.md` §Deferred Work,
`memory-bank/decisions.md`, `.workflow/` (phase punchlists, task reviews/final-reports), and
`.workflow/_dream/playbook.md`.

**Purpose:** Single taxonomy-sorted backlog for V1 gap closure, V2 rewire planning, and sprint
prioritization. Not ratified; does not modify `docs/spec.md` v1.

## How to read this document

| Column | Meaning |
|--------|---------|
| **priority** | P0 (safety-critical) → P6 (cleanup). Within a group, lower number = sooner. |
| **category** | Delivery-purpose taxonomy (see below). |
| **capability** | Subsystem or cross-cutting concern. |
| **item** | Actionable unit of work. |
| **owner** | Suggested owning role; `Owner` = product/spec owner decision. |
| **dependencies** | IDs or decisions that must land first. |
| **files touched** | Primary code/doc surfaces (not exhaustive). |
| **acceptance criteria** | Verifiable done condition. |
| **status** | `Open` · `Decision Needed` · `Accepted Deferral` · `Partial` · `Closed` |

### Delivery-purpose taxonomy

| Category | Use when |
|----------|----------|
| **V1 Gap Closure** | Correctness, silent-failure, or spec/intent mismatch in shipped v1 behavior. |
| **V2 Rewire/Architecture** | Authorization model, primitives, or structural changes that redefine how subsystems connect. |
| **Quality & Hardening** | Guards, tests, observability, production ops, contract pinning — no new product surface. |
| **Feature Enablers** | Prerequisites that unlock a gated capability without being the feature itself. |
| **V2 Features** | New operator- or analyst-visible capability in a v2 tranche. |
| **Future/Exploratory** | Roadmap items with no v1 partial implementation or no v2 design yet. |
| **Cleanup/Deprecation** | Rename, doc reconciliation, remove dead paths — no behavior change required for safety. |

### Priority scale

| Priority | Definition |
|----------|------------|
| **P0** | Silent safety inversion, authorization bypass, or fail-open on the containment path. |
| **P1** | Blocks v2 authorization rewire or operator trust in org config. |
| **P2** | Hardening required before production scale or external audit. |
| **P3** | Enabler for a gated feature (account contain, metrics, demo, detection). |
| **P4** | v2 product feature (feedback loop, progressive auth). |
| **P5** | Future/roadmap; intentional v1 scope boundary. |
| **P6** | Cleanup, optional hygiene, documentation-only. |

---

## V1 Gap Closure

### PolicyGate & containment authorization

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P0 | V1 Gap Closure | PolicyGate | **Silent skip of non-dict containment-rule `scope`** — `scope: global` and other non-dict shapes are dropped at gate time; operator `default_escalate` is a no-op while fallthrough is `ALLOW`. | Engine/Policy | — | `containment_policy.py`, `org_config_sections.py`, `preflight.py`, `configs/example_org.yaml`, `codification/sweep.py` | Preflight rejects malformed/unknown rule `scope` at activation; gate never silently ignores a declared rule; regression test for `scope: global` string. | Open |
| P0 | V1 Gap Closure | PolicyGate | **`action: escalate` does not block containment** when it is the sole matching rule; only `deny` and unresolved `auto_contain`+`escalate`/`deny` conflict block. | Engine/Policy | — | `containment_policy.py`, `gate.py`, `tests/policy/` | Target with only a matching `escalate` rule does not reach `auto_contain`; or explicit spec/decision documents escalate-as-hint-only semantics. | **Decision: escalate blocks (DEC-058); implement V2-006** |
| P1 | V1 Gap Closure | PolicyGate | **Compound-fault audit-flag drop** — stamp `FAILED` + deferred-persist conflict rebuild carries only conflict flag, drops `ticket_stamp_failed` (DEC-053 fidelity gap). | Engine | — | `engine/orchestrator.py`, `engine/edict.py`, `tests/engine/` | Rebuilt edict includes both fault flags when both conditions apply; fail-closed outcome unchanged. | Open |
| P1 | V1 Gap Closure | PolicyGate | **`ProviderUnavailableError` not caught in intake** — no Outcome Matrix row; provider fault path undefined at intake. | Engine/Judgment | Outcome Matrix row + enum | `engine/orchestrator.py`, `contracts/`, `evals/outcome_matrix.py`, `tests/engine/` | Intake maps `ProviderUnavailableError` to documented disposition + fault flag; harness scenario passes. | Open |
| P2 | V1 Gap Closure | PolicyGate | **Recovery path bypasses PolicyGate** — `engine/recovery.py` hard-downgrades `auto_contain` on stamp recovery (DEC-009); intentional but not re-evaluated through gate. | Engine | Owner decision on recovery semantics | `engine/recovery.py`, `tests/engine/` | Documented acceptance test pins behavior; or recovery re-invokes gate with pinned scenarios. | Accepted Deferral |
| P2 | V1 Gap Closure | PolicyGate | **Orphan outstanding directives** without ledger edicts skipped by startup step 6 — documented duplicate-emission risk. | Engine/Policy | — | `policy/state.py`, `tests/policy/`, `docs/contracts.md` | Reconciliation policy documented; test `test_reconcile_skips_idempotency_when_ledger_edict_missing` retained; optional purge/repair path specified. | **Resolved (DEC-060, V2-003)** — skip at step 6; health surfacing in V2-010 |
| P2 | V1 Gap Closure | PolicyGate | **v1 rate-limit scope key** uses `per_host` for all target types; org-config sliding windows / real subnet membership incomplete (DEC-030). | Engine/Policy | DEC-030 design | `policy/rate_limit.py`, `policy/containment_policy.py`, `org_config_sections.py` | Per-scope keys match DEC-030 semantics or explicit v1 limitation documented in runbook. | Partial |
| P2 | V1 Gap Closure | PolicyGate | **Emergency never-contain not evaluated in PolicyGate** — spec lists it; `gate.py` has no emergency check. | Engine/Policy | Owner: in-gate vs engine path | `policy/gate.py`, `config/emergency.py`, `tests/policy/` | Emergency entries block `auto_contain` at documented layer with harness scenario. | Open |
| P2 | V1 Gap Closure | PolicyGate | **Activation/emergency revocation paths omit ledger append** — feed + SQLite only; ledger append on startup scan / recovery edict path only. | Engine/Ledger | — | `config/activation.py`, `config/emergency.py`, `engine/recovery.py` | Revocation ledger append policy unified or explicitly documented per path. | Open |

### Containment directives & revocation

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P1 | V1 Gap Closure | Revocation | **REVIEW-008: expired-directive supersession revocation** — re-issue sets `supersedes_directive_id` but no `DirectiveRevocationRecord` / feed row; contracts §4.2 carve-out vs spec §263 tension. | Owner | — | `containment/lifecycle.py`, `revocation/`, `docs/contracts.md`, `docs/decisions.md` | Owner decision recorded in `decisions.md`; implementation matches PE-0015 or spec amendment. | **Resolved (DEC-060, V2-003)** — §4.2 carve-out ratified; no revocation on natural expiry |
| P2 | V1 Gap Closure | Revocation | **Expired-unrevoked rows** in `outstanding_containment_directives` alongside fresh re-issue (same idempotency key) — startup purge undecided. | Engine/Policy | REVIEW-008 | `containment/lifecycle.py`, `config/state.py`, `policy/state.py` | Startup step 6/7 behavior specified; no duplicate-suppression ambiguity. | **Resolved (DEC-060, V2-003)** — retain rows; exclude via `expires_at > now`; optional purge V2-010 |
| P2 | V1 Gap Closure | Revocation | **Feed supersession validation** limited to consumer-visible `reason_code`; no `superseded_by` on feed line. | Consumer SDK | — | `consumer_sdk/reference_verifier.py`, `revocation/exporter.py` | Supersession chain verifiable from feed or documented as consumer-local only. | Open |

### Never-contain audit

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P1 | V1 Gap Closure | Ledger audit | **REVIEW-007: NeverContainSnapshotRecord placement** — gate vs edict-append pairing (recommend Option 2: paired with edict). | Owner | TASK-028a wiring | `policy/gate.py`, `engine/edict.py`, `engine/orchestrator.py` | Owner decision ratified; snapshot write atomic with edict per chosen option; no duplicate snapshot writes. | **Resolved (DEC-060, V2-003)** — engine post-stamp transaction only; gate pure evaluator |

### Correlation & targeting

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P1 | V1 Gap Closure | Correlation | **Host isolation not enforced in correlator** — in-window multi-host bundles possible; citation-anchored gate is sole defense (AG-0080, REVIEW-004 strict xfail). | Correlation | — | `correlation/`, `tests/evals/test_phase3_regression_gate.py` | Correlator drops cross-host in-window noise OR documented acceptance with gate-only defense removed from xfail. | Open |
| P2 | V1 Gap Closure | Identity | **SID format validation deferred** — any non-empty string treated as SID-backed (synthetic v1). | Engine/Policy | Phase 3 identity gates | `policy/identity.py`, `correlation/` | SID format validator with pinned pass/fail vectors; or explicit v1 waiver in decisions. | Open |
| P2 | V1 Gap Closure | Identity | **Future Windows normalizers** must set `ambiguity_flag` on malformed domain-separator accounts (PE-0024). | Correlation | New normalizers | `correlation/security_log.py`, `correlation/sysmon.py` | Normalizer conformance test for ambiguity_flag rule on new event types. | Open |

### Org config & sweep

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P2 | V1 Gap Closure | Org config | **Sweep policy/statute sections remain placeholders** — sweep does not infer never-contain, subnet, or containment policy (by design); operators must hand-author. | Operator/Config | — | `codification/sweep.py`, `docs/operator_runbook.md` | Runbook states required hand-edits before activation; sweep output clearly labeled proposed-only. | Accepted Deferral |
| P3 | V1 Gap Closure | Org config | **No standalone sweep CLI** — API-only prototype (TASK-034 G-3). | Operator/Config | — | `codification/`, CLI entry if added | Documented invocation path; or CLI wrapper for sweep + preflight. | Open |

### Metrics & intake

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P2 | V1 Gap Closure | Metrics | **`record_feed_export_lag` not called from intake** — no export completion event at intake time (TASK-028a gap). | Engine/Metrics | Export hook design | `metrics/`, `engine/orchestrator.py`, `revocation/exporter.py` | Feed export lag metric populated on export completion path; documented if intentionally export-only. | Open |
| P2 | V1 Gap Closure | Metrics | **`record_llm_failure` production wiring** should restrict to `LLM_FAILURE_FAULT_FLAGS` only. | Engine/Metrics | TASK-028a metrics wiring | `metrics/`, `judgment/`, `engine/orchestrator.py` | Production call sites pass only §13 flags; test asserts rejection of policy flags. | Open |

---

## V2 Rewire/Architecture

### Authorization posture

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P0 | V2 Rewire/Architecture | PolicyGate | **Ratify authorization model** — v1 default-allow is drift, not decision; containment should be earned, not granted-by-omission (`v2_hardening` Item 2). | Owner | Independent review checklist | `docs/decisions.md`, `docs/proposals/v2_hardening.md` | Decision recorded; v2 spec section or contracts amendment drafted. | **Resolved (DEC-058, V2-001)** |
| P1 | V2 Rewire/Architecture | PolicyGate | **2a: ContainmentRule strict schema** — typed `scope`, `extra="forbid"` on `ContainmentRule`/`ContainmentPolicy`, preflight rejects malformed scope (fail loud; posture unchanged). | Engine/Config | Silent `scope` skip (P0, PolicyGate row above) | `org_config_sections.py`, `preflight.py`, `tests/config/` | Invalid scope fails preflight; example config validates; no silent rule drop. | Open |
| P1 | V2 Rewire/Architecture | PolicyGate | **2b: `default_action` catch-all primitive** — express "escalate/deny by default, allow only these groups" in one place. | Engine/Config | 2a, posture decision | `org_config_sections.py`, `containment_policy.py`, `preflight.py`, `configs/example_org.yaml` | Operator can set global default; rules override with documented precedence. | Open |
| P1 | V2 Rewire/Architecture | PolicyGate | **2b: Flip policy-layer default to deny** — no matching rule → target does not reach `auto_contain`. | Engine/Policy | 2b catch-all, posture decision | `containment_policy.py`, `gate.py`, `configs/example_org.yaml`, `evals/`, notebook | Regression: no-rule target escalates; walkthrough Case 1 + `confirmed_malicious_sequence` updated with explicit allow rules. | Open |
| P2 | V2 Rewire/Architecture | PolicyGate | **Deployment-configurable default posture** — `default_action` in org config vs hard-coded denylist/allowlist (`v2_hardening` open question). | Owner | 2b | `org_config_sections.py`, `docs/decisions.md` | Owner chooses configurable vs fixed; schema reflects choice. | **Resolved (DEC-058): configurable `default_action`; V2-012 implements** |

### Evidence authorization

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P0 | V2 Rewire/Architecture | PolicyGate | **Host `auto_contain` corroboration floor** — cited facts span ≥2 distinct `provenance_path`, ≥1 non-attacker-controllable; no sole-basis `ambiguity_flag=true` (`v2_hardening` Item 1, DEC-059). | Engine/Policy | V2-002 contract | `policy/gate.py`, `evidence/citations.py`, `evidence/provenance.py`, `evals/outcome_matrix.py`, `tests/policy/` | New fault flag `insufficient_corroboration` wired; host single-citation path escalates; harness scenario passes. | **Unblocked** — implement V2-011 |
| P1 | V2 Rewire/Architecture | PolicyGate | **Promote corroboration to first-class spec concept** — not account-only (`v2_hardening` open question). | Owner | V2-002 | `docs/contracts.md` §12a, `docs/decisions.md` DEC-059 | Spec section defines host + account corroboration symmetrically. | **Resolved (DEC-059)** |
| P2 | V2 Rewire/Architecture | PolicyGate | **Gate reads citation `provenance_path` / `ambiguity_flag` for hosts** — validator resolves them today; gate ignores for authorization (`v2_hardening` grounding). | Engine/Policy | V2-011 | `policy/gate.py`, `evidence/citations.py` | Gate authorization uses resolved citation metadata; tests pin behavior. | Open |

### Deferred-directive & intake architecture

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P2 | V2 Rewire/Architecture | Engine | **Orchestrator must consume gate directive target** — never re-derive from raw correlation bundle (AG-0080). | Engine | Correlator host isolation or accepted risk | `engine/orchestrator.py`, `policy/gate.py` | Lint or test forbids bundle-based target override on intake path. | Open |

### Contract registry

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P2 | V2 Rewire/Architecture | Contracts | **Pin `evidence_id` derivation in `docs/contracts.md`** (DEC-051, AG-0073). | Infra/Contracts | GR-0003 doc approval | `docs/contracts.md`, `hashing/domains.py`, `correlation/ids.py` | Contract § documents preimage; cross-module test matches `ids.py`. | Open |
| P2 | V2 Rewire/Architecture | Contracts | **`ContainmentRule` aligns with AG-0005** — all contract models `extra="forbid"` (playbook vs current `extra="allow"`). | Config/Contracts | 2a typed scope | `contracts/org_config_sections.py`, `tests/contracts/` | Containment models forbid unknown keys; migration path for existing configs documented. | Open |

---

## Quality & Hardening

### Test guards & eval coverage

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P2 | Quality & Hardening | Eval harness | **T1: Static guard — policy fault-flag literals ⊆ `OutcomeMatrixFaultFlag`** (phase-2/3/4 TRACK). | Engine | — | `tests/policy/`, `tests/contracts/`, `evals/outcome_matrix.py` | CI test fails on orphan gate/engine fault string not in enum. | Open |
| P2 | Quality & Hardening | State store | **T2: Production open path asserts five policy tables** under held singleton without manual `init_*`. | Engine | — | `tests/`, `state/store.py`, `policy/state.py` | `open_production_state_store` + `init_state_dir` test creates all required tables. | Open |
| P3 | Quality & Hardening | Eval harness | **T4: Optional `engine_intake` rate-counter assertion** on `auto_contain` path. | Engine | TASK-028a closed | `evals/harness.py`, `evals/scenarios/` | `engine_intake` scenario asserts rate counter row after gated contain. | Open |
| P3 | Quality & Hardening | Eval harness | **Eval-scenario regression locking discipline** — every confirmed model error becomes harness scenario (`v2_hardening` 4c). | SOC/Process | — | `evals/`, `.workflow/`, `docs/eval_gates.md` | Documented procedure; template in workflow; CI documents minimum scenario bar. | Open |
| P3 | Quality & Hardening | Eval harness | **`ledger_chain_integrity_failure` harness scenario** — startup-only; not fixture-runnable (phase-2 D2). | Engine | Production startup test harness | `tests/`, `ledger/`, `evals/` | Dedicated startup integration test OR permanent carve-out in completeness guard with rationale. | Accepted Deferral |
| P3 | Quality & Hardening | Contracts | **T5: Widen `test_scope_guard.py` allowlist** for Phase 5 docs (`operator_runbook.md`, `architecture.md`, `eval_gates.md`). | Infra | Docs landing | `tests/contracts/test_scope_guard.py` | Allowlist includes sanctioned doc paths; guard still blocks `spec.md`. | Open |
| P3 | Quality & Hardening | Outcome Matrix | **`DecisionEdict` model_validator** for fault_flag ↔ system_fault pairing (eval-only today). | Engine | — | `contracts/`, `engine/edict.py` | Pydantic validator enforces matrix polarity at edict construction. | Open |

### Ledger & feed integrity

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P2 | Quality & Hardening | Ledger | **External tip anchor for tail truncation** — `verify_chain()` cannot detect silent tail removal (AG-0027). | Infra/Ledger | Production deployment design | `ledger/`, `docs/contracts.md`, `docs/operator_runbook.md` | Limitation documented; OOB tip anchor procedure in runbook; optional verifier hook. | Open |
| P2 | Quality & Hardening | Ledger | **DB schema migrations** — `open_state_store` rejects incompatible version; no migration path (DEC-021). | Infra | — | `state/store.py`, `docs/operator_runbook.md` | Migration strategy documented or explicit v1 single-version policy. | Accepted Deferral |
| P3 | Quality & Hardening | Revocation feed | **Feed floor reconciles against on-disk file** — metadata must not outpace physical artifact (AG-0030, AG-0055). | Engine/Revocation | — | `revocation/exporter.py`, `tests/` | Crash-recovery test: stale meta → unhealthy; fresh DB → floor 0. | Partial |
| P3 | Quality & Hardening | Metrics | **MetricsCollector thread-safety** when wired to concurrent call sites (DEC-046). | Engine/Metrics | Multi-threaded wiring | `metrics/collector.py`, `docs/operator_runbook.md` | Document single-writer assumption OR add locking + concurrency test. | Open |
| P3 | Quality & Hardening | Metrics | **Metrics SQLite persistence** — in-process only in v1 (DEC-044). | Engine/Metrics | — | `metrics/`, `state/` | Persistence design doc OR explicit non-goal for v1. | Accepted Deferral |

### Detection & demo quality

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P3 | Quality & Hardening | Detection | **T7: Pin Sigma↔SPL equivalence** — per rule, matcher sets equal over manifest (phase-4 F-3). | Detection | TASK-033 | `tests/splunk/`, `tools/spl_match.py`, `detections/` | Test fails if Sigma and SPL match sets diverge for any packaged rule. | Open |
| P3 | Quality & Hardening | Detection | **T9: Splunk demo time window** — `dispatch.earliest_time = -30d` ages out 2026-06-08 fixtures. | Detection/Operator | — | `splunk/savedsearches.conf`, `splunk/README.md` | Fixture-stable window or documented refresh step; demo reproducible. | Open |
| P3 | Quality & Hardening | Detection | **T10: `tools/` mypy gate** — 4 untyped-export errors uncaught. | Infra | — | `pyproject.toml`, `tools/` | Mypy covers `tools/` OR exclusion documented in CI docs. | Open |
| P3 | Quality & Hardening | Detection | **T8: Optional `evals/run_phase4_gate.py`** single-command parity. | Detection | — | `evals/` | One command runs phase-4 checks with `--check` mode. | Open |

### Benchmark & runbook

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P3 | Quality & Hardening | Benchmark | **Burst rate measurement** in separate window (TASK-035 gap). | Engine | — | `benchmarks/serialized_path.py` | Burst metric reported separately from sustained; documented in runbook. | Open |
| P3 | Quality & Hardening | Benchmark | **Benchmark hardware specificity** — sample runs are developer-machine dependent. | Operator | — | `docs/operator_runbook.md`, `benchmarks/` | Runbook states non-gating, informational-only interpretation. | Accepted Deferral |
| P3 | Quality & Hardening | Runbook | **`init_state_dir` before `open_production_state_store`** — bootstrap WAL documented (REVIEW-005). | Operator | TASK-035 | `docs/operator_runbook.md`, `state/store.py` | Runbook prerequisite steps verified by operator checklist test topics. | Partial |

### Consumer SDK

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P3 | Quality & Hardening | Consumer SDK | **§10.6 local consumer policy check** — intentional v1 out-of-scope (phase-2 D1). | Consumer SDK | Consumer product scope | `consumer_sdk/reference_verifier.py` | Reference verifier documents §10.6 as consumer-owned; no fail-open in §10.1–10.5. | Accepted Deferral |

---

## Feature Enablers

### Account containment (Phase 3 gate)

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P3 | Feature Enablers | PolicyGate | **Enable `account_auto_contain_enabled` in production** — preflight rejects `true` until Phase 3 identity gates pass (PE-0005, spec §311). | Engine/Policy | Identity compliance tests, owner sign-off | `preflight.py`, `policy/gate.py`, `tests/config/`, `evals/` | Preflight allows flag only when identity gate evals pass; harness covers account `auto_contain`. | Open |
| P3 | Feature Enablers | PolicyGate | **Route all containment through PolicyGate** — direct `evaluate_account_containment_eligibility` callers bypass `account_containment_disabled` (PE-0014). | Engine/Policy | — | `policy/identity.py`, `policy/gate.py`, grep for direct callers | No production caller authorizes contain without gate; static or integration test enforces. | Open |

### Metrics production wiring

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P3 | Feature Enablers | Metrics | **Production metrics from real call sites** — collector built (TASK-24); feed lag at intake still open. | Engine | TASK-028a | `metrics/`, `engine/orchestrator.py` | `MetricsSnapshot` export reflects live intake/export counters; documented scrape path. | Partial |

### Org-config rate limits

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P3 | Feature Enablers | Org config | **Org-config numeric per-scope rate ceilings** — v1 fixed ceiling = 1 (phase-2 D4, DEC-029). | Engine/Config | Schema design | `org_config_sections.py`, `policy/rate_limit.py`, `preflight.py` | Org config declares per-scope limits; gate enforces configured ceilings. | Open |

### Provider integration

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P3 | Feature Enablers | Judgment | **VertexProvider real network implementation** — structural stub only (TASK-013). | Judgment | Provider credentials, DEC-047 probe policy | `judgment/vertex.py`, `judgment/provider.py`, `tests/judgment/` | Real provider obeys Protocol; probe uses synthetic canary; failures trip breaker. | Open |
| P4 | Feature Enablers | Judgment | **Live Gemini adversarial probe in CI** — probabilistic, non-gating by design (DEC-047, phase-2 D3). | Judgment | — | `evals/real_provider_adversarial.py`, `docs/eval_gates.md` | Documented manual/scheduled run; not required for CI green. | Accepted Deferral |

### Splunk demo (Phase 5)

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P3 | Feature Enablers | Detection | **T11: Live Splunk Free demo end-to-end** — Phase 5 pass criterion (phase-4 F-4). | Operator/Detection | HEC env, T9 window | `tests/splunk/`, `splunk/`, `docs/operator_runbook.md` | Env-gated HEC test passes once; five saved searches return expected `record_id`s; README reconciled for cert/`props.conf`. | Open |

### Fixtures & telemetry

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P4 | Feature Enablers | Correlation | **External OTRF/Mordor bulk fixtures** — committed sysmon/security fixtures stand in (TASK-030/031). | Correlation | — | `tests/fixtures/`, `evals/correlation_expected/` | Bulk fixtures manifest-listed OR permanent waiver with bounded local fixtures documented. | Accepted Deferral |

---

## V2 Features

### Progressive authorization

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P4 | V2 Features | PolicyGate | **Progressive authorization model** — narrow mandate, earned authority via SOC-led config promotion (`v2_hardening` Item 3). | Owner + Engine | 2b posture, override-rate metrics | `docs/decisions.md`, org config schema, runbook | Documented promotion workflow; reversible audited config changes only. | Open |
| P4 | V2 Features | Metrics | **Per-asset-class / target-type promotion reporting view** — aggregates annotations + override-rate for promotion decisions. | SOC/Engine | TASK-25 annotations, TASK-24 metrics | `metrics/`, reporting module, `docs/operator_runbook.md` | SOC lead can query override rate by asset class over window; no self-tuning. | Open |

### Feedback loop (human-in-the-middle)

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P4 | V2 Features | Judgment | **Similar-case in-context exemplars (RAG)** — retrieve human-confirmed cases into judgment prompt (`v2_hardening` 4a; plan §Deferred Work). | Judgment | Prompt slot, retrieval contract | `judgment/prompt.py`, retrieval module, `tests/judgment/` | Exemplars injected bounded/auditable; excluded from evidence hash path; A/B eval shows retrieval contract met. | Open |
| P4 | V2 Features | Org config | **Statute curation workflow** — annotation → proposed statute edit → review → re-activate (`v2_hardening` 4b). | SOC/Operator | — | `.workflow/`, `codification/`, `config/activation.py` | Tracked workflow artifact; preflight on proposed edits; activation audit trail. | Open |

### Judgment prompt

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P4 | V2 Features | Judgment | **Few-shot / exemplar slot in prompt** — not present today (`v2_hardening` grounding; prerequisite for RAG). | Judgment | — | `judgment/prompt.py` | Prompt template accepts optional exemplar block; tests verify rendering budget. | Open |

---

## Future/Exploratory

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P5 | Future/Exploratory | Enrichment | **External CTI enrichment** | — | — | TBD | PRD/spec scope item; no v1 partial impl. | Open |
| P5 | Future/Exploratory | Telemetry | **Cloud and Linux telemetry** | Correlation | Normalizers, provenance paths | `correlation/`, `evidence/` | Spec + normalizer suite for non-Windows paths. | Open |
| P5 | Future/Exploratory | Ledger | **Production WORM / external ledger storage and signed records** | Infra | Tip anchor strategy | `ledger/`, deployment | Tamper-evidence beyond SQLite hash chain. | Open |
| P5 | Future/Exploratory | Actuation | **Direct SOAR/EDR actuation adapters** | — | Emit-only v1 | — | Praetor remains emit-only; adapters out of core. | Open |
| P5 | Future/Exploratory | UI | **Analyst UI beyond annotation storage** | — | — | — | UI spec; v1 stores annotations only. | Open |
| P5 | Future/Exploratory | Containment | **Subnet and asset-group containment** (real multi-host membership) | Engine/Policy | DEC-030, asset registry | `policy/containment_policy.py`, `policy/rate_limit.py` | Directives/actuation at subnet/group scope with membership model. | Open |
| P5 | Future/Exploratory | Judgment | **Provider tokenizer API budget estimation** | Judgment | — | `judgment/` | Budget estimator integrated into prompt render path. | Open |
| P5 | Future/Exploratory | Infra | **Horizontal scaling with cross-process state-store serialization** | Infra | Single-writer v1 | `state/` | Multi-writer design + lock model documented. | Open |
| P5 | Future/Exploratory | Revocation feed | **Feed segment registry, rotation machinery, consumer cursor registration** | Engine/Consumer | — | `revocation/`, `consumer_sdk/`, `docs/plan.md` | Rotation spec; JSONL append-only v1 limitation lifted. | Open |
| P5 | Future/Exploratory | Revocation feed | **Multi-feed deployments and `revocation_feed_id` on directives** | Engine | Feed registry | `contracts/containment.py`, `revocation/` | Directives name feed ID; consumer selects feed. | Open |
| P5 | Future/Exploratory | Auth | **HTTP/API binding for write surfaces** (DEC-015) | — | TokenVerifier pluggable today | `auth/`, HTTP layer | HTTP mapping spec; role-tagged surfaces exposed. | Open |
| P5 | Future/Exploratory | Alerts | **SIEM / chat / ticket / SOAR channel implementations** | — | Outbox schema (AG-0020) | `alerts/outbox.py` | Channel adapters write delivery attempts; no schema change. | Open |
| P5 | Future/Exploratory | Annotations | **Post-decision enrichment in ledger chain** — must stay separate (AG-0066). | — | — | `analyst_annotations` pattern | Any enrichment remains outside hash chain by design. | Accepted Deferral |

---

## Cleanup/Deprecation

| priority | category | capability | item | owner | dependencies | files touched | acceptance criteria | status |
|----------|----------|------------|------|-------|--------------|---------------|---------------------|--------|
| P6 | Cleanup/Deprecation | PolicyGate | **T6: Rename `resolve_host_target` → `_resolve_host_target_legacy`** (phase-3 F-G). | Engine | — | `policy/containment_policy.py`, imports in tests | Rename done; docstring retained; no production caller regression. | Open |
| P6 | Cleanup/Deprecation | Docs | **README phase narrative reconciliation** — was Phase 2 drift (phase-3 F-E); verify still current. | Infra | — | `README.md` | Badges and task phase list match `docs/plan.md` completion state. | Partial |
| P6 | Cleanup/Deprecation | Docs | **`v2_hardening.md` independent-review checklist** — close items as decisions land. | Owner | Backlog items | `docs/proposals/v2_hardening.md` | Checklist boxes tied to `delivery_backlog.md` IDs. | Open |
| P6 | Cleanup/Deprecation | Workflow | **Phase 3/4 evidence reconciliation commits** — working-tree doc count drift (phase-4 F-2). | Infra | — | `.workflow/`, `memory-bank/` | Final-report numbers match last gate verification. | Partial |

---

## Closed (audit trail — do not schedule)

| item | closed by | notes |
|------|-----------|-------|
| PolicyGate + metrics not on production intake path (DEC-048, phase-2 F1) | TASK-028a | Tripwires converted to passing |
| Deferred directive persist until terminal stamp (DEC-053) | TASK-028a | `persist_directive=False` + post-stamp transaction |
| Attempt FSM `pending_stamp` not wired | TASK-023 | Stamp sequencing tests |
| `pending_stamp` no-row recovery unpinned | TASK-013 | Direct regression coverage |
| Startup step 6 idempotency/rate/breaker reconciliation | TASK-017/018 | `reconcile_policy_state` |
| Production benchmark wrong transaction shape | TASK-035 / DEC-056 | DEC-053 path in `benchmarks/serialized_path.py` |
| Phase 2 strict-xfail tripwires (3×) | TASK-028a | `test_policygate_integration_tripwire.py` passing |

---

## Suggested execution order (cross-category)

1. **P0 V1 gaps** — silent `scope` skip, `escalate`-does-not-block, ratify authorization model decision.
2. **P0/P1 V2 rewire foundations** — 2a strict schema, host corroboration floor, REVIEW-007/008 owner decisions.
3. **P1 V2 rewire** — 2b `default_action` + default-deny + example config / eval / notebook rewrite.
4. **P2 quality** — T1/T2 guards, correlator host isolation, ledger tip-anchor docs, compound-fault flags.
5. **P3 enablers** — account contain gate, org-config rate ceilings, Splunk live demo, metrics completeness.
6. **P4 v2 features** — progressive auth reporting, RAG exemplars, statute curation workflow.
7. **P5/P6** — roadmap exploration and cleanup as capacity allows.

---

## Related documents

- [`v2_hardening.md`](v2_hardening.md) — detailed rationale for Items 1–4
- [`../plan.md`](../plan.md) — sprint plan and §Deferred Work
- [`../decisions.md`](../decisions.md) — canonical decision log (prefer over `memory-bank/decisions.md` for new entries)
- [`.workflow/phase-3-gate-punchlist.md`](../../.workflow/phase-3-gate-punchlist.md) — TRACK T1–T6 origin
