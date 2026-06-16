# Phase 3 gate — consolidated punch-list

**Date:** 2026-06-15  
**Scope:** Tasks 28, 28a, 29, 30, 31 (correlation sprint)  
**Sources merged:** independent gate-wide verification (mechanical re-run + code/doc audit against Phase 2 carry-forward conditions and reviewer findings F-A–F-H)  
**Gate decision:** **CLEARED AS PASS-WITH-CONDITIONS 2026-06-15** — all Phase 3 pass criteria are met on fresh evidence (705 passed, 1 deselected, 1 xfailed; mypy 112 files; ruff clean; eval harness 26/26; `run_phase3_gate` 6/6; `correlation_gate` 5/5; tripwires 3/3 passing). PolicyGate is on the production intake path; end-to-end `engine_intake` evals drive gated `auto_contain` and never-contain block. Residual items are documentation debt (README, `plan.md` gate wording vs deferred persist), Phase 2 TRACK carry-forward (T1/T2 static guards), one intentional strict-xfail (REVIEW-004), and Sprint 4 scaffolding not yet present (expected).

> Unlike Phase 2 (F1 was an active production-path gap), Phase 3 closes the orchestrator wiring. The conditional pass here is for doc reconciliation and lower-risk coverage pins — not for safety-critical incompleteness.

---

## Verification actually run (not self-reported)

| Check | Command | Result |
|---|---|---|
| Test suite | `python -m pytest -q -rx` | **705 passed, 1 deselected, 1 xfailed** (REVIEW-004 strict xfail — not XPASS) |
| Types | `python -m mypy src evals consumer_sdk` | **clean, 112 source files** |
| Lint | `python -m ruff check src tests evals consumer_sdk` | **clean** |
| Phase 2+3 evals | `python -m evals.harness` | **26/26 PASS, exit 0** |
| Phase 3 gate CLI | `python -m evals.run_phase3_gate` | **6/6 PASS, exit 0** (incl. identity subprocess + phase2 harness) |
| Correlation gate CLI | `python -m evals.correlation_gate` | **5/5 PASS, exit 0** |
| Integration tripwires | `python -m pytest -q tests/engine/test_policygate_integration_tripwire.py` | **3 passed, zero xfail** |

The green suite is necessary but not sufficient: see independent gap hunt below for recovery-path semantics and partial engine_intake DB assertions.

---

## Phase 3 gate criteria (`docs/plan.md:641`) — verdicts

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Real telemetry normalization → correct provenance paths (Task 28) | **PASS** | `tests/correlation/test_correlator_identity_compliance.py:122-143` — Sysmon → `sysmon_event_log`, Security 4624 → `windows_security_log`; `tests/correlation/test_sysmon_normalization.py:58-73`; normalizers in `src/praetor/correlation/{sysmon,security_log}.py` (DEC-049 field names) |
| 2 | Identity compliance tests confirm real shapes match synthetic (Task 29) | **PASS** | `tests/correlation/test_correlator_identity_compliance.py` — 12 tests; `evals/run_phase3_gate.py:153-184` identity subprocess; `python -m evals.run_phase3_gate` → `PASS identity_compliance_evidence` |
| 3 | Correlation accuracy gate passes (Task 30) | **PASS** | `python -m evals.correlation_gate` 5/5; `evals/correlation_expected/*.yaml`; `tests/evals/test_correlation_gate.py` (19 tests) |
| 4 | Human-authored noisy expected output committed (Task 31) | **PASS** | `evals/correlation_expected/noisy_correlated_real_telemetry.yaml`; `evals/run_phase3_gate.py:120-136` `required_expected_file` |
| 5 | Account containment feature gate only after identity gates | **PASS** | `evals/run_phase3_gate.py:186-208` — preflight rejects `account_auto_contain_enabled=true` with `account_containment_prerequisite`; identity compliance required first |
| 6 | `evaluate_policy_gate` + `MetricsCollector` wired into `process_alert_intake` (Task 28a) | **PASS** (deferred persist model) | `orchestrator.py:398-406` calls gate; `:463-507` single `critical_transaction` for directive + edict + snapshot; tripwires pass; see F-A / DEC-053 |
| 7 | End-to-end `engine_intake` evals: gated `auto_contain` + never-contain block | **PASS** | `evals/scenarios/confirmed_malicious_sequence.yaml` (`runner: engine_intake`, `directive_emitted: true`); `evals/scenarios/never_contain_target.yaml` (`never_contain_snapshot`); harness 26/26 |
| 8 | Integration tripwires converted to passing (markers removed) | **PASS** | `tests/engine/test_policygate_integration_tripwire.py` — no `@pytest.mark.xfail`; **3 passed** |

---

## Phase 2 conditional-pass conditions — carry-forward status

| Condition (from `.workflow/phase-2-gate-punchlist.md`) | Status |
|---|---|
| Task 28a in plan with Task 28 dependency | **CLOSED** — `docs/plan.md` Task 28a |
| DEC-028 ratified; DEC-048 deferral recorded | **CLOSED** — `docs/decisions.md` |
| Three strict-xfail tripwires | **CLOSED** — converted to passing tests |
| Phase 3 gate requires wiring + engine_intake evals + tripwire conversion | **CLOSED** — this gate |
| README reconciled to current phase | **OPEN** — see F-E (TRACK) |
| T1 production-store table assertion | **OPEN** — see F-C (TRACK) |
| T2 policy-module fault-flag static guard | **OPEN** — see F-B (TRACK) |

---

## Reviewer findings — confirm / refute

### F-A (Medium): DEC-028 single emit vs deferred directive persist
**Status:** **CONFIRMED** (split transaction) · **PASS** (safety intent preserved)

**Confirmed:** `orchestrator.py:398-406` — `evaluate_policy_gate(..., persist_directive=False)`. Directive durability at `:463-507` inside `critical_transaction` after terminal stamp (`execute_stamp` `:420-444`). This refines DEC-028's “single serializable emit transaction” — ratified as **DEC-053** in `docs/decisions.md` (stamp ordering precedes exportable directive; edict + snapshot still co-commit with directive in the post-stamp transaction).

**Safety — no edict-without-directive export window:**
- In-flight / unknown stamp → `IntakeResult` with `edict=None`, zero outstanding directives (`test_intake_stamp_actuation.py:32-67`).
- Terminal stamp + auto_contain → directive persisted (`:70-93`).
- Deferred-persist conflict → escalate in-band, no directive (`:96-131`, `InjectNeverContainOnStampBackend`).

**No ungated containment:** gate runs before stamp; recovery path hard-downgrades `auto_contain → escalate` (`recovery.py:117-123`).

**Doc reconciliation (closed):** `docs/plan.md:641` and Task 28a body updated to reference DEC-028 + DEC-053. Canonical numbering in `docs/decisions.md`: DEC-049 = normalizer field names; DEC-053 = deferred directive persist. **Prior collision:** `memory-bank/decisions.md` had incorrectly numbered deferred persist as DEC-049 (same ID as normalizer fields in public docs) — reconciled to match canonical docs.

---

### F-B (Minor / Phase-2 T2): static fault-flag literal guard
**Status:** **CONFIRMED** — no test asserts policy-module fault literals ⊆ `OutcomeMatrixFaultFlag`.

Only transitive coverage via `tests/evals/test_eval_harness.py:62-77` (scenario flags) and runtime gate validation. DEC-052 added `ambiguous_containment_target` in two modules — drift class exists.

**Disposition:** TRACK into Sprint 4 early hygiene (add static guard test).

---

### F-C (Minor / Phase-2 T1): production store opens all five policy tables
**Status:** **CONFIRMED** — `tests/policy/test_policy_gate.py:443-450` opens with held singleton but does not assert `analyst_annotations`, `containment_rate_counters`, `circuit_breaker_state`, `provider_health_metrics`, `revocation_feed_feed_meta` exist without manual `init_*`.

Schema wiring remains correct via `open_state_store` + `reconcile_policy_state` (Phase 2 C1).

**Disposition:** TRACK into Sprint 4.

---

### F-E (Medium / docs): README Phase 2 drift
**Status:** **CONFIRMED** — badges and narrative still describe Phase 2 / Task 28a pending (`README.md:4-6`, `:32`, `:43`, `:99-109`, `:149-151`).

**Disposition:** README reconciled in gate closure (705 tests, Phase 3 complete, 32/35 tasks).

---

### F-F (Minor / tracked): `test_correlator_should_drop_cross_host_in_window_noise` strict xfail
**Status:** **CONFIRMED** — intentional **REVIEW-004** carry-forward.

`tests/evals/test_phase3_regression_gate.py:88-94` — `@pytest.mark.xfail(strict=True, reason="… REVIEW-004")`. Safe because host targeting is citation-anchored (DEC-052); gate tolerates in-window noise record 1004; correlator may still collect it. Recorded in TRACK — not a silent gap.

---

### F-G (Minor): legacy `resolve_host_target` re-introduction trap
**Status:** **PARTIALLY MITIGATED** — not a production caller issue.

- `resolve_containment_target` (`containment_policy.py:136-155`) is citation-anchored via `resolve_host_target_from_citations`; gate uses it at `gate.py:302-305`.
- `resolve_host_target` (`containment_policy.py:55-65`) retained for tests/diagnostics with docstring **“Not for PolicyGate targeting.”**
- No production module calls `resolve_host_target` for containment decisions.

**Disposition:** ACCEPT — docstring + DEC-052; optional rename to `resolve_host_target_legacy` in Sprint 4 if desired.

---

### F-F scope guard (F-H): `test_scope_guard.py` doc allowlist
**Status:** **CONFIRMED** — `tests/contracts/test_scope_guard.py:83` allowlist `{contracts,plan,decisions}` will block Phase 5 docs (`operator_runbook.md`, `architecture.md`, `eval_gates.md`).

**Disposition:** NOTE for Sprint 4/5 — widen allowlist when those docs land (same carry-forward as Phase 2 process note).

---

## independent gap hunt

| Check | Verdict | Evidence |
|---|---|---|
| Safety path bypasses `evaluate_policy_gate`? | **PASS** | `orchestrator.py:398` on intake; `skeleton_policy_result` only in `recovery.py:116` with auto_contain downgrade `:117-123`. No `skeleton_policy_result` on live intake path. |
| Intake still downgrades via skeleton stub? | **REFUTED** | Task 28a wiring live; tripwires + `confirmed_malicious_sequence` prove `auto_contain` through intake. |
| `engine_intake` evals assert DB side effects? | **PARTIAL** | `confirmed_malicious_sequence.yaml` → `_assert_directive_expectations` fetches outstanding directive row (`harness.py:125-149`). Rate counter / idempotency covered by `policy_gate` runner (`policy_gate_idempotency.yaml`) and unit tests — not re-run through `engine_intake`. Acceptable split; optional Sprint 4 eval hardening. |
| Sprint 4 Task 32 inputs present? | **MISSING (expected)** | No `detections/sigma/`, `detections/attack_mapping.yaml`, or `tests/detections/` per `docs/plan.md:587`. Task 32 not started — not a Phase 3 blocker. |

---

## TRACK — carry into Sprint 4

| ID | Item | Severity |
|---|---|---|
| T1 | Static guard: policy-module fault-flag literals ⊆ `OutcomeMatrixFaultFlag` (F-B) | Minor |
| T2 | Production `open_production_state_store` + held singleton asserts five policy tables (F-C) | Minor |
| T3 | REVIEW-004: correlator drops cross-host in-window noise (strict xfail today) | Minor |
| T4 | Optional: `engine_intake` eval asserts rate-counter row on `auto_contain` path | Minor |
| T5 | Widen scope guard for Phase 5 operator docs (F-H) | Note |
| T6 | Optional: rename `resolve_host_target` → `_resolve_host_target_legacy` (F-G) | Note |

---

## ACCEPT-AS-DEFERRED

| Item | Basis |
|---|---|
| Compound-fault stamp+deferred-persist rebuild drops `ticket_stamp_failed` on conflict path | DEC-053 known fidelity gap; fail-closed; rare under single-writer v1 |
| `engine_intake` idempotency/rate-counter not duplicated | Covered by `policy_gate` scenarios + unit tests |
| Sprint 4 detection scaffolding absent | Task 32 scope starts Sprint 4 |

---

## GATE DECISION

**PASS-WITH-CONDITIONS**

**Rationale:** All eight Phase 3 gate criteria pass on independently re-run mechanical checks. Phase 2 F1 (PolicyGate not on production path) is **closed**. Safety-critical paths are fail-closed. Conditions are non-blocking doc/coverage debt:

1. **T1 (F-B):** add static fault-flag literal guard before or during Task 32.
2. **T2 (F-C):** pin production-store table existence test.
3. **T3 (F-F / REVIEW-004):** tracked strict-xfail; revisit when correlator noise policy changes.
4. **README + plan gate text:** reconciled in gate closure (DEC-053 ratified; README Phase 3 state).
5. **Sprint 4 entry:** `detections/` tree absent — expected until Task 32.

**Sprint 4 may start** (Task 32 — Sigma rule packaging).
