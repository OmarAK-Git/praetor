# DEBT_LEDGER — Recoverable MVP-Era Traces

**Status:** Structured probe extract as of 2026-07-18.  
**Method:** Fixed probes only — comment markers, git-log debt language, hardcoded constants, swallowed exceptions, single-impl abstractions, complexity thresholds, untested paths, pinned dependencies.  
**Companion:** `AS_BUILT.md` (what the system is).  
**Rule:** Every entry cites a findable artifact. Speculative “probably debt” items are excluded.

---

## How to read this ledger

| Severity | Meaning |
|---|---|
| **S1** | Silent/unsafe degradation or production stub on a safety boundary |
| **S2** | Config/duplication drift or provisional pin that can diverge |
| **S3** | Complexity / coverage / process debt — recoverable but not urgent |
| **INFO** | Intentional product deferral (documented) — tracked for completeness |

IDs: `DEBT-###` stable for this extract.

---

## Probe A — Comment debt (`TODO` / `FIXME` / `HACK`)

**Result: no classic markers in `src/` or `tests/`.**

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| DEBT-001 | INFO | Sweep “placeholder” language is a **feature** (activation-blocking sentinels), not unfinished work | `codification/models.py` `SWEEP_PLACEHOLDER_SENTINELS`; `placeholders.py`; preflight `unreplaced_sweep_placeholder` |
| DEBT-002 | S3 | Stale fixture README still says Task-1 “manifest stub” / “extended later” | `tests/fixtures/README.md` |

False positives filtered: `tempfile.NamedTemporaryFile` / `TemporaryDirectory` (stdlib).

---

## Probe B — Git log debt signals

Searched subjects/bodies for: `for now`, `temporary`, `simplify`, `hack`, `mvp`, `stub`, `placeholder`, `workaround`, `quick`, `later`, `TODO`, `FIXME`, `WIP`, `tech debt`.

| ID | Severity | Commit | Signal | Notes |
|---|---|---|---|---|
| DEBT-010 | S2→verify | `109ff8a` | body: “default-allow unchanged **for now**”; deferred work | Historical; largely addressed by DEC-058 / V2-012+. Confirm no residual default-allow paths remain (preflight + policy tests suggest closed). |
| DEBT-011 | INFO | `0873e3e` | “Vertex provider **stub**” | Evolved into `VertexProvider`; Fake still used for CI |
| DEBT-012 | INFO | `ad22055`, `38e3ca0` | README / fixture “stub” / “placeholder” | Scaffold-era |
| DEBT-013 | INFO | `afbbb4f` | “sweep **placeholder** safety” | Hardening of intentional sentinels |
| DEBT-014 | S3 | `2b6a612` | “checkpoint before checking out master” | Process noise in history |
| DEBT-015 | INFO | `a01fca9`, `689d35a` | “tracked integration **deferral**” | Phase 2 conditional pass — intentional tracking |

No hits for: `temporary`, `simplify`, `hack`, `mvp`, `workaround` as standalone debt commits.

---

## Probe C — Swallowed / quiet exceptions

**Bare `except:` / `except …: pass`:** none in `src/praetor`.

| ID | Severity | Location | Pattern | Classification |
|---|---|---|---|---|
| DEBT-020 | **S1** | `policy/state.py` ~209–210 | `except Exception: return False` | Silent — idempotency register failure treated as skip; overly broad |
| DEBT-021 | **S1** | `revocation/feed.py` ~184–185 | `(FeedChecksumError, ValidationError) → return None` | Quiet — corrupt on-disk line ignored with no log |
| DEBT-022 | **S1** | `annotations/precedent.py` ~87–88 | `ValidationError → return None` | Quiet — invalid ledger edict skipped for precedent with no log |
| DEBT-023 | INFO | `config/live.py` ~83–84, 116–117 | `PreflightError → False/continue` | Intentional — skip malformed never-contain entries |
| DEBT-024 | INFO | `policy/containment_policy.py` ~209–210 | `AttributeError → continue` | Intentional — skip non-object exclusion entries |
| DEBT-025 | INFO | `tickets/stamp.py` ~133–136 | `BaseException` → `StampStatus.UNKNOWN` when ambiguous | Documented degradation |
| DEBT-026 | S3 | `ledger/store.py` ~144–150 | Broad `except Exception` then typed re-raise | Awkward shape, not a swallow |
| DEBT-027 | INFO | `alerts/system_health.py` ~75–87 | Catch → record FAILED delivery | Intentional durable failure |
| DEBT-028 | INFO | `auth/verifier.py`, `config/loader.py`, `config/live.py` | Broad catch → typed wrap | Fail-closed wraps |

---

## Probe D — Hardcoded / duplicated constants

### Named module constants (documented — track drift only)

| Constant | Value | Location |
|---|---|---|
| `HARD_CONFIG_CHARACTER_BUDGET` | `400_000` | `config/constants.py` |
| `DIRECTIVE_MAX_SECONDS` | `300` | `config/constants.py` |
| `EMERGENCY_MAX_SECONDS` | `48 * 3600` | `config/constants.py` |
| `DEFAULT_FEED_PROPAGATION_SECONDS` | `60` | `config/constants.py` |
| `DEFAULT_CLOCK_SKEW_SECONDS` | `30` | `config/constants.py` |
| `DEFAULT_CORRELATION_WINDOW_SECONDS` | `300` | `correlation/window.py` |
| `V1_DEFAULT_MAX_PROVIDER_JUDGMENT_LATENCY_SECONDS` | `30` | `engine/timeouts.py` — **explicitly provisional** |
| Prompt bounds | `200` / `3` / `400` | `judgment/excerpt.py` |
| Vertex defaults | `gemini-2.0-flash`, `60.0s`, Google API base URL | `judgment/vertex_provider.py` |
| `_V1_DEFAULT_SCOPE_LIMIT` | `1` | `policy/state.py` — “until Task 18 org-config limits” |

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| DEBT-030 | **S2** | Provisional latency SLA not org-config-pinned | `engine/timeouts.py` docstring + constant `30` |
| DEBT-031 | **S2** | Emergency max seconds defined twice | `config/constants.py` `EMERGENCY_MAX_SECONDS` vs `config/emergency.py` `EMERGENCY_HARD_MAX_SECONDS` (both `48*3600`) |
| DEBT-032 | **S2** | Directive 300s triplicated | `constants.DIRECTIVE_MAX_SECONDS`, `contracts.DIRECTIVE_MAX_LIFETIME`, sweep template literal |
| DEBT-033 | **S2** | Sweep `_DEFAULT_POLICY_TEMPLATE` hardcodes policy numbers instead of importing constants | `codification/sweep.py` ~50–75: `300`, `172800`, breaker `60`/`5`/`3`/`10`, feed `60`/`3`, queue `120`, rate targets `30`/`60` |
| DEBT-034 | S3 | Unnamed magic `detail[:500]` truncation | `judgment/vertex_provider.py` |
| DEBT-035 | INFO | Only hardcoded external URL: Gemini API base | `judgment/vertex_provider.py` |
| DEBT-036 | S3 | Rate-limit scope still host-local for asset groups | DEC-030 partial; `policy/state.py` / rate_limit paths |

---

## Probe E — Single-implementation abstractions

No ABCs. Five `Protocol`s:

| ID | Severity | Protocol | Production impls | Debt |
|---|---|---|---|---|
| DEBT-040 | **S1** | `TicketStampBackend` | Only `SucceedingStampBackend` / `_NoOpStampBackend` | **Zero real ticket/SOAR backend** — stamp boundary is stubbed |
| DEBT-041 | **S1** | `TokenVerifier` | Only `PrincipalMapVerifier` (dev/test map) | **No production IdP adapter** (IdP issuance is non-goal, but write surfaces still need a real verifier for deploy) |
| DEBT-042 | S2 | `FeedJsonlSink` | Only `FileFeedJsonlSink` | Protocol notes “v1: no rotation” |
| DEBT-043 | INFO | `HealthAlertSink` | `JsonlSink` + `StdoutSink` | Two sinks = accepted v1 set; SIEM/chat deferred |
| DEBT-044 | INFO | `JudgmentProvider` | `FakeProvider` + `VertexProvider` | Two impls — Fake is CI default for evals, not engine default |

---

## Probe F — Complexity threshold

**Threshold:** functions ≥80 LOC; files ≥400 LOC; high branch density.

### Files ≥400 LOC

| LOC | Path | ID |
|---:|---|---|
| 822 | `engine/orchestrator.py` | DEBT-050 |
| 538 | `policy/gate.py` | DEBT-051 |
| 518 | `judgment/provider_health_breaker.py` | DEBT-052 |
| 499 | `revocation/exporter.py` | DEBT-053 |
| 431 | `state/store.py` | DEBT-054 |
| 427 | `codification/sweep.py` | DEBT-055 |
| 418 | `config/state.py` | DEBT-056 |

### Functions ≥80 LOC

| Approx LOC | Function | Path | ID |
|---:|---|---|---|
| 322 | `process_alert_intake` | `engine/orchestrator.py` | DEBT-057 |
| 220 | `evaluate_policy_gate` | `policy/gate.py` | DEBT-058 |
| 120 | `build_progressive_authorization_report` | `reporting/progressive_authorization.py` | DEBT-059 |
| 108 | `_build_summary` | `codification/sweep.py` | DEBT-060 |
| 89 | `export_next_pending_row` | `revocation/exporter.py` | DEBT-061 |
| 88 | `add_emergency_never_contain` | `config/emergency.py` | DEBT-062 |
| 82 | `recover_single_attempt` | `engine/recovery.py` | DEBT-063 |
| 82 | `_build_absence_of_evidence_risks` | `codification/report.py` | DEBT-064 |

### Highest branch-density files

| Branches (heuristic) | Nested≥8 | Path | ID |
|---:|---:|---|---|
| 63 | 13 | `config/preflight.py` | DEBT-065 |
| 44 | 10 | `policy/gate.py` | (see DEBT-051) |
| 40 | 15 | `policy/containment_policy.py` | DEBT-066 |
| 40 | 14 | `ledger/hash_chain.py` | DEBT-067 |
| 28 | 10 | `engine/recovery.py` | DEBT-068 |

Severity for DEBT-050–068: **S3** (maintainability / review load).

---

## Probe G — Untested / weakly tested paths

| ID | Severity | Path / surface | Evidence |
|---|---|---|---|
| DEBT-070 | **S2** | `config.internal.purge_expired_emergency_records_internal` | No positive test; deliberately not exported |
| DEBT-071 | S3 | `correlation.window` / `correlation.excerpts` | No dedicated tests; only via `correlate_telemetry` |
| DEBT-072 | S3 | `engine.citations` | Thin wrapper; no direct unit test |
| DEBT-073 | S3 | No `tests/reporting/` package tree | Covered only via `tests/metrics/test_progressive_authorization_reporting.py` |
| DEBT-074 | S3 | No `tests/retrieval/` package tree | Covered only via `tests/judgment/test_similar_case_retrieval.py` |
| DEBT-075 | S3 | `config.live` | Indirect coverage only via emergency/activation/preflight |
| DEBT-076 | INFO | `.gitignore` contains bare `state/` | Footgun for any `state/` dir; `src/praetor/state/` currently tracked |

---

## Probe H — Documented deferred surfaces (intentional debt)

From `docs/plan.md`, `docs/spec.md`, `docs/proposals/v2_implementation_plan.md`, DECs:

| ID | Severity | Deferred surface | Doc / code pin |
|---|---|---|---|
| DEBT-080 | INFO | Direct SOAR/EDR actuation adapters | Spec non-goals; only directive emission |
| DEBT-081 | INFO | HTTP/API binding for write surfaces | Spec; library APIs only |
| DEBT-082 | INFO | Feed rotation / segment registry / consumer cursors | Spec + `FeedJsonlSink` docstring |
| DEBT-083 | INFO | Cloud / Linux telemetry | Spec non-goals |
| DEBT-084 | INFO | External CTI enrichment | Spec non-goals |
| DEBT-085 | INFO | Multi-host auto-containment (DEC-052 Option C) | DEC-052 C1–C5 gates |
| DEBT-086 | INFO | Real subnet / multi-host asset-group membership | DEC-030; sweep uses placeholders |
| DEBT-087 | INFO | Horizontal scaling / cross-process serialization | Spec deferred work |
| DEBT-088 | INFO | SIEM/chat delivery channels beyond JSONL/stdout | Alerts package v1 sinks |
| DEBT-089 | INFO | MetricsCollector not thread-safe | Module docs / v1 single-writer |
| DEBT-090 | INFO | SID form validation does not yet gate `is_sid_backed` | DEC-062 waiver |
| DEBT-091 | INFO | Consumer SDK local policy check (§10 item 6) not implemented | `consumer_sdk/reference_verifier.py` |
| DEBT-092 | INFO | Recovery bypasses PolicyGate re-evaluation | Spec + delivery backlog acceptance |
| DEBT-093 | INFO | Walking-skeleton naming retained in engine facade | `WalkingSkeletonEngine` still exported |

---

## Probe I — Dependencies / reproducibility

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| DEBT-100 | **S2** | **No lockfile** (`uv.lock` / `poetry.lock` / `requirements*.txt` absent) | Repo root; installs not bit-reproducible |
| DEBT-101 | S2 | Runtime deps lower-bound only | `pydantic>=2.0`, `PyYAML>=6.0` in `pyproject.toml` |
| DEBT-102 | S3 | Build backend unpinned | `hatchling` in `[build-system].requires` |
| DEBT-103 | INFO | Only meaningful upper pin | `pysigma-backend-splunk>=1.1,<3` (dev optional) |
| DEBT-104 | INFO | Python floor only | `requires-python = ">=3.11"` |

---

## Priority board (actionable first)

### S1 — fix or explicitly accept with monitoring

1. **DEBT-040** — Real `TicketStampBackend` or document deploy-time stub requirement  
2. **DEBT-041** — Production `TokenVerifier` adapter for write surfaces  
3. **DEBT-020** — Narrow/log idempotency `except Exception` in `policy/state.py`  
4. **DEBT-021 / DEBT-022** — Log (or metric) quiet `return None` skips in feed/precedent paths  

### S2 — drift / reproducibility

5. **DEBT-100 / DEBT-101** — Add lockfile or pin ranges  
6. **DEBT-030** — Promote latency SLA into org-config contract  
7. **DEBT-031 / DEBT-032 / DEBT-033** — Single-source constants; sweep template imports them  
8. **DEBT-010** — One-time verification that “for now” default-allow is fully retired  
9. **DEBT-070** — Test or delete unused emergency purge internal  

### S3 — maintainability / coverage hygiene

10. Split or modularize `process_alert_intake` / `evaluate_policy_gate` (DEBT-057/058)  
11. Package-local tests for `reporting` / `retrieval` / correlation window (DEBT-071–074)  
12. Refresh `tests/fixtures/README.md` (DEBT-002)  

### INFO — keep on roadmap, do not treat as bugs

DEBT-080–093 (documented non-goals and accepted deferrals).

---

## Probe coverage checklist

| Probe | Status |
|---|---|
| A Comment markers | Done — clean except INFO sentinels + fixture README |
| B Git log debt language | Done — table above |
| C Swallowed exceptions | Done |
| D Hardcoded constants | Done |
| E Single-impl Protocols | Done |
| F Complexity ≥80 LOC / ≥400 file | Done |
| G Untested paths | Done |
| H Documented deferrals | Done |
| I Pinned deps / lockfile | Done |

---

## Document control

| Field | Value |
|---|---|
| Generated | 2026-07-18 |
| Companion | `AS_BUILT.md` |
| Live task plan | `IMPLEMENTATION_PLAN.md` (extraction complete) |
