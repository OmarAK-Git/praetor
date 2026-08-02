# AS_BUILT — Praetor Reverse Specification

**Status:** Reverse-engineered from the repository as of 2026-07-18.  
**Method:** Structured extraction probes (module inventory, interfaces, data flows, invariants claimed-vs-enforced, error posture, test coverage map).  
**Not:** Product intent docs. For claimed behavior see `docs/spec.md`, `docs/contracts.md`, `docs/architecture.md`. This document describes **what the system actually is**.

---

## 0. System identity

Praetor is a **post-detection disposition-policy engine** for a SOC. Detection has already fired; Praetor decides what happens next.

| Property | As built |
|---|---|
| Version | `0.1.0` (`src/praetor/__init__.py`, `pyproject.toml`) |
| Language | Python ≥3.11 |
| Runtime deps | `pydantic≥2.0`, `PyYAML≥6.0` |
| Package layout | `src/praetor/` (hatchling wheel) |
| Durable store | SQLite WAL (`praetor.state.StateStore`) |
| Dispositions | Exactly three: `standard_review` \| `escalate` \| `auto_contain` (no `auto_close`) |
| Actuation | Emits `ContainmentDirective` contracts; **does not** call EDR/SOAR |
| Authority | LLM proposes (`ModelJudgment`); deterministic **PolicyGate** authorizes |

Canonical pipeline (implemented):

```text
Alert intake → Correlation → Judgment (LLM) → PolicyGate → Stamp → Ledger
                                    ↓
                          ContainmentDirective → Revocation feed (JSONL)
Operator-adjacent: reporting · similar-case retrieval · statute curation
```

---

## 1. Module inventory

### 1.1 Package layout

| Package | Path | Role |
|---|---|---|
| `contracts` | `src/praetor/contracts/` | Versioned Pydantic domain models; schema export |
| `hashing` | `src/praetor/hashing/` | Canonical JSON + domain-separated ID/hash derivations |
| `runtime` | `src/praetor/runtime/` | Process singleton lock; production state-store open |
| `state` | `src/praetor/state/` | SQLite store, attempts, idempotency, critical transactions |
| `config` | `src/praetor/config/` | Org-config load/preflight/activate; emergency never-contain |
| `correlation` | `src/praetor/correlation/` | Sysmon/Security → `EvidenceBundle` + prompt excerpts |
| `judgment` | `src/praetor/judgment/` | Provider protocol, prompts, Fake/Vertex, health breaker |
| `evidence` | `src/praetor/evidence/` | Citation validation; host/account corroboration |
| `policy` | `src/praetor/policy/` | PolicyGate, rate limits, breakers, containment policy |
| `engine` | `src/praetor/engine/` | Intake orchestrator + startup recovery |
| `tickets` | `src/praetor/tickets/` | Stamp outbox + pluggable stamp backend |
| `alerts` | `src/praetor/alerts/` | SystemHealthAlert outbox + JSONL/stdout sinks |
| `ledger` | `src/praetor/ledger/` | Hash-chained append-only audit SoR |
| `revocation` | `src/praetor/revocation/` | Feed exporter (JSONL projection) |
| `containment` | `src/praetor/containment/` | Directive lifecycle + revocation |
| `auth` | `src/praetor/auth/` | Token/role checks on write surfaces (not an IdP) |
| `metrics` | `src/praetor/metrics/` | In-process counters + PolicyGate evaluation rows |
| `reporting` | `src/praetor/reporting/` | Read-only progressive-authorization report |
| `retrieval` | `src/praetor/retrieval/` | Similar-case ranking for prompt exemplars |
| `annotations` | `src/praetor/annotations/` | Analyst annotations + human-confirmed precedents |
| `codification` | `src/praetor/codification/` | Org-config sweep CLI + statute curation (review-only) |

Adjacent (not under `src/praetor/`):

| Area | Path | Role |
|---|---|---|
| Consumer SDK | `consumer_sdk/` | Reference pre-actuation verifier |
| Evals | `evals/` | Deterministic scenario harness + phase gates |
| Schemas | `schemas/` | Generated JSON Schema from contracts |
| Detections | `detections/` | Sigma rules + compiled SPL |
| Tools | `tools/` | Schema export, Sigma compile, fixtures |

### 1.2 Per-package detail

#### `engine`
- **Purpose:** End-to-end intake (correlate → judge → gate → stamp → ledger) and startup recovery.
- **Key APIs:** `process_alert_intake`, `WalkingSkeletonEngine`, `run_engine_startup_recovery`, `build_decision_edict`.
- **Primary file:** `orchestrator.py` (~822 LOC; `process_alert_intake` ~322 LOC).
- **Deps out:** nearly all packages. **Deps in:** judgment, state, tests/evals.

#### `policy`
- **Purpose:** Deterministic authorization of proposed dispositions, especially `auto_contain`.
- **Key APIs:** `evaluate_policy_gate`, `evaluate_target_containment_policy`, `resolve_containment_target`, rate/breaker state.
- **Primary file:** `gate.py` (~538 LOC; `evaluate_policy_gate` ~220 LOC).

#### `correlation`
- **Purpose:** Normalize Windows Sysmon/Security telemetry into `EvidenceBundle` + excerpts within a time window and host isolation.
- **Key APIs:** `correlate_telemetry`, `normalize_sysmon_event`, `normalize_security_event`, `derive_evidence_id`.
- **Behavior pin (DEC-050):** unsupported EventIDs are skipped; empty bundle does not raise — orchestrator maps empty → `correlation_failure`.

#### `judgment`
- **Purpose:** LLM judgment surface.
- **Key APIs:** `JudgmentProvider` protocol, `call_provider_with_retries`, `FakeProvider`, `VertexProvider`, prompt builders, provider-health breaker.
- **Callers must inject a provider** — no production default baked into engine.

#### `containment`
- **Purpose:** Outstanding directive lifecycle and never-contain conflict revocation.
- **Key APIs:** `build_proposed_directive_in_transaction`, `commit_outstanding_directive`, `manual_revoke_directive`, `revoke_directives_matching_never_contain`.

#### `ledger`
- **Purpose:** Hash-chained system of record for edicts, never-contain snapshots, emergencies, revocations.
- **Key APIs:** `append_ledger_record`, `verify_ledger_chain`, `run_ledger_startup_hook`.
- **Startup:** broken chain → health alert + refuse to start.

#### `tickets`
- **Purpose:** Durable stamp outbox; stamp precedes ledger append (DEC-053).
- **Key APIs:** `execute_stamp`, `TicketStampBackend` protocol.
- **Production backends:** only `SucceedingStampBackend` / `_NoOpStampBackend` stubs — no real SOAR/ticket adapter.

#### `config`
- **Purpose:** Load, preflight, snapshot-hash, activate org statute; live/emergency never-contain.
- **Key APIs:** `activate_org_config`, `run_preflight`, `add_emergency_never_contain`, `promote_statute_curation`.

#### `contracts`
- **Purpose:** Shared domain models; `export_schemas` → `schemas/*.json`.
- **Exports:** `AlertEnvelope`, `EvidenceBundle`, `ModelJudgment`, `DecisionEdict`, `ContainmentDirective`, `OrgConfigSnapshot`, `PolicyGateResult`, ledger/feed/health/governance models, `Disposition`.

#### `auth`
- **Purpose:** Role checks on external write surfaces.
- **Surfaces:** `org_config_activation` / `emergency_never_contain` (`soc_lead`); `annotation_submission` (`analyst`).
- **Only verifier impl:** `PrincipalMapVerifier` (dev/test map).

#### `alerts`
- **Purpose:** Durable health-alert outbox; v1 sinks = JSONL + stdout.
- **Not on hash chain.**

#### `annotations` / `retrieval` / `reporting`
- Annotations store human feedback; retrieval ranks precedents into prompt exemplars (outside evidence-hash path); reporting aggregates PolicyGate overrides read-only. None auto-tune org config.

#### `codification`
- Sweep produces **proposed** org-config (preflight-rejected until SOC promotion). CLI: `python -m praetor.codification`.

#### `hashing`
- Single canonical serializer (`canonical.py`); domain constants only in `domains.py`. Library-only; no inbound praetor deps.

#### `revocation`
- Append-only JSONL feed projection for consumers; export health gates new `auto_contain`. Not audit SoR.

#### `runtime` / `state`
- Production path: acquire `SingletonLock` → `open_production_state_store` → schema init → ledger verify → attempt recovery → feed startup.

#### `metrics`
- Optional `MetricsCollector` on intake; durable `policy_gate_evaluations` rows on edict commit.

---

## 2. Interfaces

### 2.1 Library entrypoints

| Surface | Module | Summary |
|---|---|---|
| `process_alert_intake` | `engine/orchestrator.py` | One alert through full path → `IntakeResult` |
| `WalkingSkeletonEngine` | `engine/orchestrator.py` | Thin facade around intake |
| `run_engine_startup_recovery` | `engine/recovery.py` | Spec recovery steps 4–7 |
| `open_state_store` | `state/store.py` | Schema + ledger verify + recovery + feed hook |
| `open_production_state_store` | `runtime/startup.py` | Requires held singleton; asserts policy tables |
| `activate_org_config` | `config/activation.py` | Auth → preflight → revoke conflicts → activate |
| `add_emergency_never_contain` | `config/emergency.py` | Auth’d emergency exclusion |
| `evaluate_policy_gate` | `policy/gate.py` | Deterministic gate (+ optional directive persist) |
| `execute_stamp` | `tickets/stamp.py` | Outbox + backend stamp |
| `export_pending_feed_rows` | `revocation/exporter.py` | Drain feed outbox → JSONL |
| `submit_annotation` | `annotations/store.py` | Auth’d analyst annotation |
| `retrieve_similar_case_exemplars` | `retrieval/similar_cases.py` | Precedent ranking |
| `export_schemas` | `contracts/schema_export.py` | Regenerate `schemas/` |
| Hash helpers | `hashing/` | `derive_decision_id`, `derive_idempotency_key`, `derive_stamp_id`, `canonical_serialize`, feed checksums |

`praetor.__init__` exposes only `__version__`. No `console_scripts` in `pyproject.toml`.

### 2.2 Protocols (no ABCs)

| Protocol | Defined | Production implementations |
|---|---|---|
| `JudgmentProvider` | `judgment/provider.py` | `FakeProvider`, `VertexProvider` |
| `TicketStampBackend` | `tickets/stamp.py` | `SucceedingStampBackend`, `_NoOpStampBackend` (stubs) |
| `TokenVerifier` | `auth/verifier.py` | `PrincipalMapVerifier` only |
| `HealthAlertSink` | `alerts/system_health.py` | `JsonlSink`, `StdoutSink` |
| `FeedJsonlSink` | `revocation/exporter.py` | `FileFeedJsonlSink` only |

### 2.3 CLI / tooling

| Invocation | Role |
|---|---|
| `python -m praetor.codification` | Org-config sweep (proposed artifacts) |
| `python -m praetor.contracts.schema_export` | Schema regenerate |
| `python tools/schema_export.py --check\|--write` | Schema drift gate |
| `tools/compile_sigma.py`, `evals/*.py` | Detection compile / eval harnesses |

### 2.4 Schema / consumer contracts

Committed schemas under `schemas/` (14 contract models + eval scenario schema). Field shape SoT = generated JSON Schema; meaning/derivations SoT = `docs/contracts.md`.

Consumer SDK: `consumer_sdk/reference_verifier.py` — `verify_directive_pre_actuation` implements contracts §10 items 1–5; local policy item 6 **not** implemented.

### 2.5 Auth write surfaces

| Surface | Role | Write API |
|---|---|---|
| `org_config_activation` | `soc_lead` | `activate_org_config` / `promote_statute_curation` |
| `emergency_never_contain` | `soc_lead` | `add_emergency_never_contain` |
| `annotation_submission` | `analyst` | `submit_annotation` |

Internal-only ops (`LEDGER_APPEND`, `DIRECTIVE_EMISSION`, `FEED_EXPORT`) rejected by external auth helpers.

---

## 3. Data flows

### 3.1 Durable stores

| Store | Kind | Role |
|---|---|---|
| `processing_attempts` | SQLite | Attempt lifecycle; ≤1 non-terminal per alert |
| `completed_decisions` | SQLite | Three-tuple PK completed edicts |
| `idempotency_keys` | SQLite | Active containment idempotency |
| `ticket_stamp_outbox` | SQLite | Stamp pending/succeeded/failed/unknown |
| `ledger_chain` | SQLite | Hash-chained audit SoR |
| `org_config_*` / `active_org_config` | SQLite | Bound statute |
| `emergency_never_contain_records` | SQLite | Live emergency exclusions |
| `outstanding_containment_directives` | SQLite | Unexpired directives |
| `directive_revocation_records` + feed outbox/meta | SQLite | Revocation SoR + export cursor |
| Feed JSONL | File beside DB | Consumer delivery projection |
| `system_health_*` | SQLite | Health alerts (not chained) |
| Rate/breaker/provider-health tables | SQLite | Gate state |
| `analyst_annotations` | SQLite | Governance + similar-case input |
| `policy_gate_evaluations` | SQLite | Override metrics |

### 3.2 Happy path `auto_contain`

Concrete chain in `process_alert_intake`:

1. `fetch_active_snapshot` — require active org config  
2. Correlate / resolve evidence → hash bundle → prompt excerpts  
3. `allocate_attempt` (return existing completed if three-tuple matches)  
4. Similar-case exemplars → judgment prompt → `JudgmentProvider.generate_judgment`  
5. Citation validation → `evaluate_policy_gate(..., persist_directive=False)`  
6. `execute_stamp` (outbox + backend)  
7. Single `critical_transaction`: deferred directive persist (re-check feed/never-contain/rate) + ledger append + attempt finalize + evaluation row  

### 3.3 Downgrade / escalate paths

Fault short-circuits finish with escalate + Outcome Matrix fault flags (correlation failure, config over budget, provider faults, invalid citation, latency/queue, PolicyGate blocks). Stamp failure preserves candidate disposition and adds `ticket_stamp_failed`. Deferred persist conflict rebuilds escalate edict in-band.

### 3.4 Startup recovery

`open_state_store` / `open_production_state_store`:

1. Singleton + SQLite WAL/IMMEDIATE guards  
2. Schema init  
3. Ledger chain verify — **refuse start** on break  
4. `run_engine_startup_recovery` — resolve attempts; **force `AUTO_CONTAIN` → `ESCALATE`**; reconcile policy state; revoke never-contain conflicts  
5. Feed export recovery — if SLO missed, degraded non-actuating mode  

### 3.5 Org-config activation + never-contain revoke

`activate_org_config`: auth → preflight → TX (revoke matching outstanding directives, retire absorbed emergencies, activate snapshot) → flush health alerts. Emergency path mirrors revoke-on-conflict.

### 3.6 Revocation feed export

Revocation writers → pending outbox → `export_pending_feed_rows` → JSONL with checksum. PolicyGate consults `is_feed_actuation_blocked` for new `auto_contain`.

### 3.7 Annotation → similar-case → prompt

`submit_annotation` → later intake `retrieve_similar_case_exemplars` → bounded exemplar block in judgment prompt only (does not mutate org config).

---

## 4. Invariants: claimed vs enforced

| # | Claimed | Enforced where | Gap |
|---|---|---|---|
| 1 | No `auto_close` | `Disposition` StrEnum + schemas | None |
| 2 | Stamp before ledger (DEC-053) | Intake: stamp then TX directive+edict; stamp sequencing tests | Fault paths use `stamp_status=not_required` (intentional) |
| 3 | PolicyGate sole containment authority | Intake always gates; boundary guard tests | Recovery hard-escalates without re-gate (accepted) |
| 4 | Never-contain blocks contain | Gate snapshot/live/emergency; deferred re-check | None for auth |
| 5 | Broken ledger → refuse start | `run_ledger_startup_hook` → `LedgerStartupError` | Only if callers use store open hooks |
| 6 | Recovery never emits containment | `_recovery_disposition_for_stamp` downgrade + tests | Not PolicyGate re-eval |
| 7 | Required `default_action`; no omission-allow (DEC-058) | Pydantic + preflight + containment policy | Explicit `default_action: allow` still permitted |
| 8 | Host corroboration floor (DEC-059) | Gate → `insufficient_corroboration` | Account path separate; SID form waiver DEC-062 |
| 9 | Unhealthy feed blocks `auto_contain` | Gate + deferred persist + exporter | Non-contain dispositions still allowed |
| 10 | Three-tuple completed-edict idempotency | `completed_decisions` PK + allocate_attempt | Distinct from `decision_id` (includes attempt) |
| 11 | Domain-separated hashes | `domains.py` + grep guard in hashing tests | None |
| 12 | Canonical serialization strict | `canonical_serialize` raises; hashing tests | Unknown-field reject needs `allowed_keys` at call site |
| 13 | Length-delimited multi-input hashes | `delimited()` in all derive_* | None |
| 14 | Containment idempotency suppress | `derive_idempotency_key` + gate insert | Rate-scope `per_asset_group` still host-local (DEC-030) |
| 15 | One non-terminal attempt per alert | Partial unique index + allocate_attempt | None |
| 16 | Emergency cannot authorize containment | Emergency only on exclusion lists | None |
| 17 | Account contain behind feature gate | Gate flag + preflight | Eligibility helper can signal AUTO_CONTAIN; production must use gate |
| 18 | Citation-anchored host targeting (DEC-052) | `resolve_containment_target` | Multi-host auto-contain deferred (Option C) |
| 19 | Health/feed not on hash chain | Ledger allow-list; separate outboxes | None |
| 20 | Auth on write surfaces only | `WriteSurface` + role map | Library APIs — callers must pass tokens |
| 21 | Provider non-authoritative | Gate can always downgrade | Judgment quality not machine-gated (claimed) |
| 22 | Stable `stamp_id` across attempts | `derive_stamp_id` without attempt id | Backend must be idempotent (documented residual risk) |
| 23 | Outcome Matrix coupling | Enums + eval harness + engine finishers | Not every cell has a dedicated unit file |
| 24 | Sole `escalate` rule blocks contain | Containment policy evaluation | Closed V2-006 |
| 25 | Startup order ledger→recovery→feed | `open_state_store` sequence | None for that entrypoint |

---

## 5. Error-handling posture

### 5.1 Dominant pattern: fail loud into Outcome Matrix

Intake maps typed provider/system failures to escalate + fault flags via `_finish_*` helpers — never silent drop of an alert. PolicyGate blocks become escalate with specific flags (`never_contain_*`, `insufficient_corroboration`, `revocation_feed_unhealthy`, …).

### 5.2 Fail closed (raise / refuse)

| Situation | Behavior |
|---|---|
| Ledger chain broken at startup | Raise `LedgerStartupError`; refuse intake |
| Singleton lock unavailable | Exit / raise; no dual writers |
| Canonical serialization violation | `CanonicalSerializationError` — never hash partial input |
| Auth failure | Typed auth errors; fail closed |
| Config load/preflight | Wrap → `ConfigLoadError` / `PreflightError` |
| No active org config | Intake raises `RuntimeError` |

### 5.3 Intentional degradation (recorded, not silent)

| Situation | Behavior |
|---|---|
| Health alert sink write fail | Record delivery FAILED; continue |
| Stamp ambiguous timeout | `StampStatus.UNKNOWN` (documented) |
| Malformed live never-contain entry | Skip match (`PreflightError` → continue/false) |
| Deferred directive persist conflict | Rebuild escalate edict; no outstanding directive |
| Feed unhealthy | Block `auto_contain` only; allow review/escalate |

### 5.4 Quiet / broad catches (see DEBT_LEDGER)

| Location | Behavior |
|---|---|
| `policy/state.py` | `except Exception: return False` on idempotency register |
| `revocation/feed.py` | checksum/validation error → `return None` |
| `annotations/precedent.py` | invalid edict JSON → `return None` |

### 5.5 What does **not** raise

- Correlation: unsupported EventIDs skipped; empty bundle returned (orchestrator escalates).
- Sweep CLI: exits non-zero on failure rather than throwing through library APIs.
- MetricsCollector: best-effort counters; not thread-safe (v1 single-writer assumption).

---

## 6. Test coverage map

### 6.1 Package → tests

| Source package | Primary tests | Coverage notes |
|---|---|---|
| `engine` | `tests/engine/` (10 files) | Core path well covered; `citations.py` thin wrapper untested directly |
| `policy` | `tests/policy/` (10 files) | Gate, corroboration, breakers, boundary |
| `ledger` | `tests/ledger/` (8 files) | Chain, startup, tip anchor, incomplete rows |
| `config` | `tests/config/` (6 files) | Activation, gate, emergency, loader; `internal.py` / `live.py` weak direct coverage |
| `correlation` | `tests/correlation/` (6 files) | Normalizers, host isolation, evidence_id; `window.py`/`excerpts.py` indirect |
| `judgment` | `tests/judgment/` (5 files) | Provider failures, Vertex, breaker, prompt, similar-case |
| `evidence` | `tests/evidence/` (4 files) | Citations, host/account corroboration, SID |
| `contracts` | `tests/contracts/` (7 files) | Validators, roundtrip, schema, guards |
| `tickets` | `tests/tickets/` (2 files) | Outbox + sequencing |
| `containment` | `tests/containment/` (3 files) | Lifecycle, revocation, DEC-060 feed |
| `revocation` | `tests/revocation/test_feed_exporter.py` | `feed.py`/`outbox.py` via exporter |
| `runtime` | `tests/runtime/` (3 files) | Startup guard, production init, feed recovery |
| `state` | `tests/state/test_attempt_lifecycle.py` | Single suite for core store |
| `alerts` | `tests/alerts/test_system_health_outbox.py` | |
| `annotations` | `tests/annotations/test_annotations.py` | Precedents also via judgment similar-case |
| `codification` | `tests/codification/` (3 files) | Sweep, CLI, statute curation |
| `hashing` | `tests/hashing/test_canonical.py` | |
| `auth` | `tests/auth/test_auth_primitives.py` | |
| `metrics` | `tests/metrics/` (4 files) | Includes progressive-auth reporting |
| `reporting` | **no `tests/reporting/`** | Covered via metrics progressive-auth test |
| `retrieval` | **no `tests/retrieval/`** | Covered via judgment similar-case test |

### 6.2 Cross-cutting

| Area | Tests |
|---|---|
| Evals harness / phase gates | `tests/evals/` |
| Benchmarks | `tests/benchmarks/` |
| Consumer SDK | `tests/consumer_sdk/` |
| Sigma / Splunk | `tests/detections/`, `tests/splunk/` |
| Docs drift | `tests/docs/test_docs.py` |
| Smoke | `tests/test_smoke.py` |

### 6.3 Eval posture

- Deterministic harness: `evals/harness.py` + scenarios under `evals/scenarios/`.
- Default pytest excludes `@integration` and `@probabilistic` (`pyproject.toml` `addopts`).
- Phase 3 / correlation / provider-unavailable gates under `evals/` + `tests/evals/`.

### 6.4 Weak / indirect coverage candidates

- `config.internal.purge_expired_emergency_records_internal` — no positive test  
- `correlation.window` / `correlation.excerpts` — only via `correlate_telemetry`  
- `engine.citations` — thin re-export of evidence validation  
- `reporting` / `retrieval` packages — no package-local test trees  

---

## 7. Composition at runtime (summary)

```text
open_production_state_store
  → SingletonLock + StateStore
  → ledger verify (refuse if broken)
  → run_engine_startup_recovery (never emit containment)
  → feed startup (may set degraded)

process_alert_intake
  → active org snapshot
  → correlate → evidence hash
  → allocate_attempt (idempotent three-tuple)
  → similar cases → judgment provider
  → citations → PolicyGate (persist_directive=False)
  → stamp outbox
  → critical_transaction:
       deferred directive persist (if still auto_contain)
       + ledger edict (+ never-contain snapshot)
       + complete attempt
       + record gate evaluation
```

---

## 8. Explicit non-capabilities (as built)

These are absent from the codebase, not merely undocumented:

- HTTP/API server binding for write surfaces  
- Real ticket/SOAR/EDR adapters  
- Production IdP / token issuance (`PrincipalMapVerifier` only)  
- Feed rotation / segment registry / consumer cursor registration  
- Cloud/Linux telemetry normalizers  
- Horizontal scaling / multi-process writers  
- Self-tuning policy from annotations  
- Multi-host auto-containment (DEC-052 Option C blocked)  

---

## Document control

| Field | Value |
|---|---|
| Generated | 2026-07-18 |
| Companion | `DEBT_LEDGER.md` |
| Sources | `src/praetor/**`, `tests/**`, `docs/{spec,architecture,contracts,decisions}.md`, `schemas/`, `pyproject.toml`, git history probes |
