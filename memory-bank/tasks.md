# Tasks

## V1 — complete

All **35** plan tasks in `docs/plan.md` are done (pytest **778** at TASK-035 close). Evidence and history: **Done (V1)** below.

## V2 — active

Index of `docs/proposals/v2_implementation_plan.md` (**36** tasks, **6** sprints, **6** phase gates).

| ID | Task | Sprint | Status | Depends | Cx |
|---|---|---|---|---|---|
| V2-001 | Authorization Posture Decision | V2-0 | **complete** | — | M |
| V2-002 | Host Corroboration Contract | V2-0 | **complete** | — | M |
| V2-003 | Revocation and Snapshot Owner Decisions | V2-0 | **complete** | — | M |
| V2-004 | Provider Unavailable Outcome Matrix Row | V2-0 | **complete** | — | S |
| V2-005 | Strict ContainmentRule Schema and Scope Preflight | V2-1 | **complete** | V2-001 | L |
| V2-006 | Escalate Rule Blocks Containment | V2-1 | **complete** | V2-001, V2-005 | M |
| V2-007 | ProviderUnavailable Intake Handling | V2-1 | **complete** | V2-004 | M |
| V2-008 | Compound Fault Flag Preservation | V2-1 | **complete** | — | M |
| V2-009 | Emergency Never-Contain Gate Alignment | V2-1 | **complete** | V2-003 | M |
| V2-010 | Recovery Policy Pinning | V2-1 | **complete** | V2-003 | M |
| V2-011 | Host Auto-Contain Corroboration Floor | V2-2 | **complete** | V2-002 | L |
| V2-012 | Default Action Primitive | V2-2 | **complete** | V2-001, V2-005, V2-006 | L |
| V2-013 | Default-Deny or Configurable Posture Flip | V2-2 | **complete** | V2-012 | L |
| V2-014 | Correlator Host Isolation | V2-2 | **complete** | V2-011 | L |
| V2-015 | Gate Target Ownership Guard | V2-2 | **complete** | V2-011, V2-014 | M |
| V2-016 | Static Policy Fault-Flag Guard | V2-2 | **complete** | V2-011, V2-015 | M |
| V2-017 | Production State Initialization Guard | V2-3 | **complete** | V2 Gate 2 | M |
| V2-018 | Revocation Supersession and Feed Verifiability | V2-3 | **complete** | V2 Gate 2 | L |
| V2-019 | Ledger Tip Anchor and Feed Floor Hardening | V2-3 | **complete** | V2-017 | L |
| V2-020 | Metrics Production Completeness | V2-3 | **complete** | V2-017, V2-016 | L |
| V2-021 | Evidence ID Contract Pin | V2-3 | **complete** | V2 Gate 2 | M |
| V2-022 | SID and Normalizer Conformance | V2-3 | **complete** | V2 Gate 2 | M |
| V2-023 | Contract Scope Guard and Generated Artifact Hygiene | V2-3 | **complete** | V2-021, V2-016 | M |
| V2-024 | Account Containment Production Enablement | V2-4 | **complete** | V2 Gate 3, V2-011, V2-016, V2-022 | L |
| V2-025 | All Containment Through PolicyGate | V2-4 | **complete** | V2-024 | M |
| V2-026 | Org-Config Numeric Rate Ceilings | V2-4 | **complete** | V2 Gate 3, V2-012 | M |
| V2-027 | Org-Config Sweep CLI | V2-4 | **complete** | V2 Gate 3 | M |
| V2-028 | Real Vertex Provider Implementation | V2-4 | **complete** | V2 Gate 3 | L |
| V2-029 | Detection and Splunk Demo Durability | V2-4 | **complete** | V2 Gate 3 | M |
| V2-030 | Benchmark Burst Measurement and Runbook Pins | V2-4 | **complete** | V2 Gate 3, V2-020 | M |
| V2-031 | Consumer Policy and Feed Roadmap Boundary | V2-4 | **complete** | V2-018, V2-019 | M |
| V2-032 | Progressive Authorization Reporting | V2-5 | **complete** | V2-020, V2-026 | L |
| V2-033 | Judgment Prompt Exemplar Slot | V2-5 | **complete** | — | M |
| V2-034 | Similar-Case Retrieval | V2-5 | **complete** | V2-032, V2-033 | L |
| V2-035 | Statute Curation Workflow | V2-5 | **complete** | V2-027, V2-032 | L |
| V2-036 | Eval Regression Locking Discipline | V2-5 | **complete** | V2-034, V2-035 | M |

**Next up:** Judgment capability spike sprint complete (build only). Live
capture + labeled manifest + Gemini run remain operator-owned. Enrichment-split
and V2 through Gate 5 are complete.

| ID | Goal | Status | Depends |
|---|---|---|---|
| capability-spike-01-corpus | Anchor manifest schema/loader | **done** | — |
| capability-spike-02-flatten | Generic event flattener | **done** | 01 |
| capability-spike-03-bundle | Path B bundle builder | **done** | 02 |
| capability-spike-04-runner | Observation + two-path runner | **done** | 03 |
| capability-spike-05-score | Scoring / A/B delta / confound | **done** | 04 |
| capability-spike-06-cli | CLI + eval_gates docs | **done** | 05 |
| capability-spike-gate | phase_exit full suite + harness | **done** | 01–06 |

Design: `docs/superpowers/specs/2026-08-01-capability-spike-design.md`  
Plan: `docs/superpowers/plans/2026-08-01-judgment-capability-spike.md`

Full V2 task definitions: **`docs/proposals/v2_implementation_plan.md`**.

## V2 — upcoming (by sprint)

| Sprint | Tasks | Theme |
|---|---|---|
| V2-0 | V2-001 – V2-004 | Decision and contract ratification |
| V2-1 | V2-005 – V2-010 | Safety-critical V1 gap closure |
| V2-2 | V2-011 – V2-016 | Authorization rewire foundations |
| V2-3 | V2-017 – V2-023 | State, ledger, feed, and metrics hardening |
| V2-4 | V2-024 – V2-031 | Feature enablers and operator readiness |
| V2-5 | V2-032 – V2-036 | V2 product features (reporting, exemplars, statute curation) |

## V2 — task index

| ID | Task | Depends |
|---|---|---|
| V2-001 | Authorization Posture Decision | — |
| V2-002 | Host Corroboration Contract | — |
| V2-003 | Revocation and Snapshot Owner Decisions | — |
| V2-004 | Provider Unavailable Outcome Matrix Row | — |
| V2-005 | Strict ContainmentRule Schema and Scope Preflight | V2-001 |
| V2-006 | Escalate Rule Blocks Containment | V2-001, V2-005 |
| V2-007 | ProviderUnavailable Intake Handling | V2-004 |
| V2-008 | Compound Fault Flag Preservation | — |
| V2-009 | Emergency Never-Contain Gate Alignment | V2-003 |
| V2-010 | Recovery Policy Pinning | V2-003 |
| V2-011 | Host Auto-Contain Corroboration Floor | V2-002 |
| V2-012 | Default Action Primitive | V2-001, V2-005, V2-006 |
| V2-013 | Default-Deny or Configurable Posture Flip | V2-012 |
| V2-014 | Correlator Host Isolation | V2-011 |
| V2-015 | Gate Target Ownership Guard | V2-011 |
| V2-016 | Static Policy Fault-Flag Guard | V2-004, V2-011 |
| V2-017 | Production State Initialization Guard | — |
| V2-018 | Revocation Supersession and Feed Verifiability | V2-003 |
| V2-019 | Ledger Tip Anchor and Feed Floor Hardening | V2-017 |
| V2-020 | Metrics Production Completeness | V2-007, V2-016 |
| V2-021 | Evidence ID Contract Pin | — |
| V2-022 | SID and Normalizer Conformance | V2-011 |
| V2-023 | Contract Scope Guard and Generated Artifact Hygiene | V2-005, V2-016, V2-021 |
| V2-024 | Account Containment Production Enablement | V2-011, V2-016, V2-022 |
| V2-025 | All Containment Through PolicyGate | V2-024 |
| V2-026 | Org-Config Numeric Rate Ceilings | V2-012 |
| V2-027 | Org-Config Sweep CLI | — |
| V2-028 | Real Vertex Provider Implementation | V2-007 |
| V2-029 | Detection and Splunk Demo Durability | — |
| V2-030 | Benchmark Burst Measurement and Runbook Pins | V2-020 |
| V2-031 | Consumer Policy and Feed Roadmap Boundary | V2-018, V2-019 |
| V2-032 | Progressive Authorization Reporting | V2-020, V2-026 |
| V2-033 | Judgment Prompt Exemplar Slot | — |
| V2-034 | Similar-Case Retrieval | V2-032, V2-033 |
| V2-035 | Statute Curation Workflow | V2-027, V2-032 |
| V2-036 | Eval Regression Locking Discipline | V2-034, V2-035 |

## V2 — phase gates

| Gate | Required tasks | Pass criteria (summary) |
|---|---|---|
| V2 Gate 0 | V2-001 – V2-004 | Authorization posture, host corroboration, snapshot/revocation placement, provider-unavailable mapping ratified |
| V2 Gate 1 | V2-005 – V2-010 | Malformed scope fails activation; escalate cannot permit containment; provider unavailable mapped; compound faults preserved; emergency never-contain blocks; recovery pinned |
| V2 Gate 2 | V2-011 – V2-016 | Host corroboration required; explicit default posture; correlator/gate target ownership enforced; fault flags cannot drift |
| V2 Gate 3 | V2-017 – V2-023 | Production table init; revocation/feed consumer-verifiable; metrics wired; evidence IDs pinned; scope guards strict |
| V2 Gate 4 | V2-024 – V2-031 | Account containment enablement; all containment through PolicyGate; rate ceilings; sweep CLI; real provider; Splunk demo resolved |
| V2 Gate 5 | V2-032 – V2-036 | Read-only promotion reporting; bounded exemplars; human-confirmed retrieval; statute curation review-only; eval regression discipline |

## V2 — carry-forward from V1

- `ProviderUnavailableError` intake mapping ratified in V2-004 (DEC-061); V2-007 extends metrics/breaker test coverage.
- Static fault-flag guard, production-store table init tracked into V2-016/V2-017.
- Live Splunk HEC demo remains env-gated (V2-029).
- Phase 4 gate PASS-WITH-CONDITIONS items close in V2-029.

## V2 — governing constraints (summary)

- `docs/contracts.md` remains SSOT for hashes, IDs, Outcome Matrix fault flags.
- Intake: DEC-053 deferred directive persist — `evaluate_policy_gate(..., persist_directive=False)` then one `critical_transaction`.
- PolicyGate target selection uses gate-resolved target, not raw bundle re-derivation.
- Recovery must not emit new auto-containment unless explicit owner decision supersedes v1 rule.
- Proposed org-config sweep artifacts remain non-activatable.
- Marker-gated tests for real providers / live Splunk; fixture-backed tests in default suite.

## V2 — complete (Gate 0 + Gate 1 + Gate 2)

| ID | Task | Evidence |
|---|---|---|
| V2-001 | Authorization Posture Decision | `.workflow/V2-001/verification.md` — DEC-058; pytest 780 |
| V2-002 | Host Corroboration Contract | `.workflow/V2-002/verification.md` — DEC-059; contracts §12a/§13 |
| V2-003 | Revocation and Snapshot Owner Decisions | `.workflow/V2-003/verification.md` — DEC-060; contracts §4.2.1/§7a (gate-evaluation `snapshot_content` timing); pytest 785 |
| V2-004 | Provider Unavailable Outcome Matrix Row | `.workflow/V2-004/verification.md` — DEC-061; contracts §13; pytest 785 |
| V2-005 | Strict ContainmentRule Schema and Scope Preflight | `.workflow/V2-005/verification.md` — typed scope + preflight; pytest 791 |
| V2-006 | Escalate Rule Blocks Containment | `.workflow/V2-006/verification.md` — escalate/deny block; distinct fault flags; pytest 799 |
| V2-007 | ProviderUnavailable Intake Handling | `.workflow/V2-007/verification.md` — breaker + metrics on intake; scoped pytest 161 |
| V2-008 | Compound Fault Flag Preservation | `.workflow/V2-008/verification.md` — DEC-053 compound fault flags pinned; pytest 27 (task-scoped) |
| V2-009 | Emergency Never-Contain Gate Alignment | `.workflow/V2-009/verification.md` — gate authorization + intake harness; scoped pytest 154 |
| V2-010 | Recovery Policy Pinning | `.workflow/V2-010/verification.md` — DEC-060 orphan alerts + recovery downgrade pinned; scoped pytest 247 |
| V2-011 | Host Auto-Contain Corroboration Floor | `.workflow/V2-011/verification.md` — insufficient_corroboration wired; harness 31/31 |
| V2-012 | Default Action Primitive | `.workflow/V2-012/verification.md` — `default_action` schema + preflight + policy fallback; pytest 834 |
| V2-013 | Default-Deny or Configurable Posture Flip | `.workflow/V2-013/verification.md` — explicit allowlist posture; eval harness 31/31; pytest 836 |
| V2-014 | Correlator Host Isolation | `.workflow/V2-014/verification.md` — anchor-host filter; xfail removed; pytest 842 |
| V2-015 | Gate Target Ownership Guard | `.workflow/v2-015-gate-target/results/verifier-result.md` — `resolved_target` ownership; AG-0080 enforced; scoped pytest 125 |
| V2-016 | Static Policy Fault-Flag Guard | `.workflow/v2-016-fault-flag-guard/results/verifier-result.md` — literals ⊆ OutcomeMatrixFaultFlag; edict flag/SFE validation; scoped pytest 208 |
| V2 Gate 2 exit | Authorization Rewire phase exit | `.workflow/v2-gate-2-exit/results/verifier-result-final.md` — full pytest 856 / ruff clean / mypy clean (122 files) |

## Done (V1 — recent)

| ID | Task | Evidence |
|---|---|---|
| TASK-035 | Production Throughput Benchmark and Operator Runbooks | `.workflow/TASK-035/verification.md` — 7 benchmark + 10 doc tests; pytest 778; operator runbook + architecture |
| TASK-034 | Empirical Org-Config Sweep Prototype | `.workflow/TASK-034/verification.md` — 17 codification tests; pytest 778; preflight blocks proposed artifacts |
| TASK-033 | SPL Compilation and Splunk Demo Harness | `.workflow/TASK-033/verification.md` — 21 splunk tests; compile `--check`; pytest 744 |
| TASK-031 | Phase 3 Harness on Correlated Telemetry | `.workflow/TASK-031/verification.md` — DEC-052 citation-anchored targeting; phase3 gate GREEN; pytest 705 |
| TASK-030 | Correlation Accuracy Gate | `.workflow/TASK-030/verification.md` — 19 gate tests; pytest 685; `python -m evals.correlation_gate` 4/4 PASS |
| TASK-029 | Correlator Identity Compliance Tests | `.workflow/TASK-029/verification.md` — 12 tests in default suite; policy-gate e2e; pytest 666 |
| TASK-028a | Production Orchestrator PolicyGate and Metrics Integration | `.workflow/TASK-028a/verification.md` — pytest 646; eval harness 24/24; tripwires pass |

## Done (V1 — full)

| ID | Task | Evidence |
|---|---|---|
| TASK-001 | Repository structure and test harness | `.workflow/task-001/verification.md` — `pytest` 2 passed; hatchling + Python 3.11+ |
| TASK-002 | Versioned contract models | `.workflow/task-002/verification.md` — 14 models, `schemas/` export, 36 `pytest` passed |
| TASK-003 | Canonical serialization and hash constants | `.workflow/TASK-003/verification.md` — `pytest` 62 passed; `docs/contracts.md` §5/§7; `src/praetor/hashing/` |
| TASK-004 | Authenticated write surface primitives | `.workflow/TASK-004/verification.md` — `pytest` 90 passed; `src/praetor/auth/` |
| TASK-005 | SQLite startup guard and process singleton | `.workflow/TASK-005/verification.md` — `pytest` 107 passed; `src/praetor/runtime/`, `src/praetor/state/sqlite_guard.py` |
| TASK-006 | SQLite state store and attempt lifecycle | `.workflow/TASK-006/verification.md` — `pytest` 152 passed, 32 Task-6 tests; `src/praetor/state/{store,attempts,completed_decisions,idempotency}.py` |
| TASK-007 | Ticket stamp outbox | `.workflow/TASK-007/verification.md` — `pytest` 173 passed, 21 Task-7 tests; reopen hardening pass |
| TASK-008 | SystemHealthAlert outbox | `.workflow/TASK-008/verification.md` — `pytest` 196 passed, 23 Task-8 tests; reopen hardening pass |
| TASK-009 | Org config loader, preflight, activation, emergency never-contain | `.workflow/TASK-009/verification.md` — `pytest` 254 / config 55; contracts §3a; flight recorder closed |
| TASK-010 | Hash-chained audit log and snapshot records | `.workflow/TASK-010/verification.md` — `pytest` 285 / ledger 29; contracts §7a; startup hook |
| TASK-011 | Revocation feed exporter, startup recovery, smoke benchmark | `.workflow/TASK-011/verification.md` — `pytest` 302 / revocation 11; `src/praetor/revocation/` |
| TASK-012 | Walking skeleton decision flow and recovery | `.workflow/TASK-012/verification.md` — `pytest` 341 / engine 25; `src/praetor/engine/` — **Phase 1 gate** |
| PHASE-1-GATE | Gate closure punch-list | `.workflow/phase-1-gate-punchlist.md` — `python -m pytest -q` 343 passed; `python -m mypy src` clean; `python -m ruff check src tests` clean |
| TASK-013 | Provider abstraction / FakeProvider injection modes | `.workflow/TASK-013/verification.md` — `pytest` 354 / judgment 10 / engine 26; `src/praetor/judgment/`; `pending_stamp` no-row recovery regression |
| TASK-014 | Prompt construction and excerpt hygiene | `.workflow/TASK-014/verification.md` — `pytest` 359 / judgment 15 / engine 26; `src/praetor/judgment/{excerpt,prompt}.py`; sanitized `PromptExcerptSet` provider payload |
| TASK-015 | Evidence Citation Validator | `.workflow/TASK-015/verification.md` — `pytest` 366 / evidence 7 / engine-provider citations 15; `src/praetor/evidence/citations.py`; shared validator for structural citation refs |
| TASK-016 | Canonical Account Identity and Synthetic Provenance Tests | `.workflow/TASK-016/verification.md` — `pytest` 395 / evidence corroboration 20; `src/praetor/evidence/provenance.py`, `src/praetor/policy/identity.py`; synthetic fixtures under `tests/fixtures/synthetic/` |
| TASK-017 | Deterministic PolicyGate v1 | `.workflow/TASK-017/verification.md` — `pytest` 416 / policy 21; `src/praetor/policy/{gate,containment_policy,directive_builder,state}.py`; startup step 6 + `open_production_state_store` |
| TASK-018 | Transactional Rate Limits and Containment Breaker | `.workflow/TASK-018/verification.md` — `pytest` 434 / policy 39; `src/praetor/policy/{rate_limit,circuit_breaker}.py`; sliding-window scopes + containment breaker alerts |
| TASK-019 | Provider-Health Breaker with Half-Open Probes | `.workflow/TASK-019/verification.md` — `pytest` 462 / judgment 25; gatekeeper: cooldown, startup init, tx guards |
| TASK-020 | Directive Lifecycle and Revocation | `.workflow/TASK-020/verification.md` — `pytest` 485 / containment 23 (lifecycle 15, revocation 8); manual revocation ledger (DEC-034); `src/praetor/containment/` |
| TASK-021 | Reference Consumer Verifier | `.workflow/TASK-021/verification.md` — `pytest` 509 / consumer_sdk 24; gatekeeper: expiry skew (DEC-037), supersession hole, checksum, gap (DEC-038); `consumer_sdk/reference_verifier.py` |
| TASK-022 | Latency SLA and Queue Aging | `.workflow/TASK-022/verification.md` — `pytest` 523 / engine latency+queue 14; gatekeeper: DEC-039 cumulative retry, DEC-040 recovery-only queue aging; `src/praetor/engine/{timeouts,queue_policy}.py` |
| TASK-023 | Ticket Stamp Contract Integration | `.workflow/TASK-023/verification.md` — `pytest` 543 / tickets stamp sequencing 20; gatekeeper: DEC-042 fault-flag preservation, DEC-043 redelivery raises; `src/praetor/tickets/contract.py` |
| TASK-024 | Metrics | `.workflow/TASK-024/verification.md` — `pytest` 556 / metrics 13; `src/praetor/metrics/{collector,events}.py`; in-process collector for all Task 24 criteria |
| TASK-025 | Analyst Annotation Storage | `.workflow/TASK-025/verification.md` — `pytest` 578 / annotations 8; `src/praetor/annotations/store.py`; auth + schema validation + decision linkage |
| TASK-026 | Mandatory Phase 2 Eval Harness | `.workflow/TASK-026/verification.md` — `pytest` 615 / evals 33; `evals/harness.py` + 24 scenario YAML; full Outcome Matrix + completeness guard |
| TASK-027 | Real-Provider Adversarial Excerpt Probe | `.workflow/TASK-027/verification.md` — `pytest` 629 / evals 47; `evals/real_provider_adversarial.py`; mocked Gemini path + payload structural checks; `docs/eval_gates.md` |
| TASK-028 | Correlation Normalization and PromptExcerptSet | `.workflow/TASK-028/verification.md` — `pytest` 638 / correlation 9; `src/praetor/correlation/`; Sysmon+Security normalization, process graph, window filter, PromptExcerptSet |
| TASK-032 | Sigma Rule Repository | `.workflow/TASK-032/verification.md` — 18 detection tests; 5 sigma rules; pytest 723 |
| PHASE-4-GATE | Detection portability gate (Tasks 32–33) | `.workflow/phase-4-gate-punchlist.md` — PASS-WITH-CONDITIONS; pytest 744 (39 detection+splunk); mypy 112 clean; ruff clean; `compile_sigma.py --check` exit 0; offline SPL match audit |
