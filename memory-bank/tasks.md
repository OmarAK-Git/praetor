# Tasks

Index of `docs/plan.md` (35 tasks, 5 sprints).

## Active

| ID | Task | Status | Notes |
|---|---|---|---|
| TASK-030 | Correlation Accuracy Gate | Next | Depends on Task 28 |

## Done (recent)

| ID | Task | Evidence |
|---|---|---|
| TASK-029 | Correlator Identity Compliance Tests | `.workflow/TASK-029/verification.md` — 12 tests in default suite; policy-gate e2e; pytest 666 |
| TASK-028a | Production Orchestrator PolicyGate and Metrics Integration | `.workflow/TASK-028a/verification.md` — pytest 646; eval harness 24/24; tripwires pass |

## Gate prerequisites

- Startup recovery step 6 is implemented in TASK-017 (`reconcile_policy_state`).
- Engine orchestrator still uses skeleton inline policy; wire PolicyGate into intake as follow-on.
- Provider-health breaker (`praetor.judgment.provider_health_breaker`) is implemented; wire production failure recording into intake as follow-on.
- `ProviderUnavailableError` maps via `provider_failure_trips_breaker()` but is not caught in intake until an Outcome Matrix row exists.
- TASK-015 citation surface (TASK-017 reuse): citable field paths are normalized
  evidence fields (bare or `normalized_fields.*`), nested normalized paths, plus
  `source_event_reference` and `provenance_path` (TASK-014 prompt excerpts).
  `raw_source` is unciteable at any path depth. Fact-envelope keys such as
  `evidence_id` are not citable field paths.

## Upcoming (by phase)

| Phase | Tasks | Pass criteria (summary) |
|---|---|---|
| Phase 2 — Judgment & policy | 13–27 | PolicyGate, eval harness (mandatory scenarios), metrics, reference consumer verifier |
| Phase 3 — Correlation | 28–31 | Real telemetry normalization, identity compliance, correlation gate |
| Phase 4 — Detection portability | 32–33 | Sigma repo, SPL/Splunk demo |
| Phase 5 — Codification & ops | 34–35 | Config sweep prototype, production benchmark, operator runbooks |

Full task definitions, tests-first criteria, and file paths: **`docs/plan.md`**.

## Done

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
| TASK-028a | Production Orchestrator PolicyGate and Metrics Integration | `.workflow/TASK-028a/verification.md` — `pytest` 653; deferred directive persist (DEC-049); eval 25/25; tripwires pass |
| TASK-029 | Correlator Identity Compliance Tests | `.workflow/TASK-029/verification.md` — 12 tests; policy-gate on real fixtures; pytest 666 |
