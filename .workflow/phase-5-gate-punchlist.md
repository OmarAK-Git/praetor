# Phase 5 gate — consolidated punch-list

**Date:** 2026-06-16  
**Scope:** Tasks 34, 35 (operator readiness sprint)  
**Sources merged:** gatekeeper Sprint 5 validation (F1–F5 remediation), independent criteria re-derivation against `docs/plan.md` Task 34/35 and Phase 5 pass criteria, fresh mechanical re-run.  
**Gate decision:** **CLEARED AS PASS-WITH-CONDITIONS 2026-06-16** — all automatable Phase 5 criteria pass on fresh evidence (**778 passed**, 2 deselected, 1 xfailed; mypy **118** files clean; ruff clean incl. `benchmarks`; codification **17**, benchmark **7**, docs **10**; production benchmark **14402.3** alerts/min sustained vs target **30**/min on this hardware). Residual: live Splunk Free demo remains operator-executed (env-gated skip test, not CI proof).

> Unlike Phase 4 (detection portability), Phase 5 closes operator-facing codification and throughput measurement. The conditional pass is for manual-only Splunk demo execution — not for safety-critical Sprint 5 gaps in sweep preflight or benchmark fidelity.

---

## Verification actually run (not self-reported)

| Check | Command | Result |
|---|---|---|
| Codification tests | `python -m pytest -q tests/codification/` | **17 passed** |
| Production benchmark tests | `python -m pytest -q tests/benchmarks/test_serialized_path.py` | **7 passed** |
| Operator doc tests | `python -m pytest -q tests/docs/` | **10 passed** |
| Self-contained benchmark | `python -m evals.run_phase5_benchmark` | **exit 0** — sustained **14402.3**/min vs target **30**/min (`meets_sustained_target=True`); elapsed **0.125** s / 30 ops |
| Full suite | `python -m pytest -q` | **778 passed**, 2 deselected, 1 xfailed (REVIEW-004 strict xfail — unchanged) |
| Types | `python -m mypy src evals consumer_sdk` | **clean, 118 source files** |
| Lint | `python -m ruff check src tests evals consumer_sdk benchmarks` | **clean** |

Fresh-checkout benchmark gate: `evals/run_phase5_benchmark.py` opens a temp DB, activates `configs/example_org.yaml`, runs 30 DEC-053 iterations — no pre-existing `state/bench.db` required (F1 closed).

---

## Reviewer findings — confirm / refute / close

### F1 — Phase 5 gate command not runnable as documented
**Status:** **CONFIRMED** → **CLOSED.**

`python -c "...run_serialized_path_benchmark(Path('state/bench.db')..."` raised `ValueError` on fresh checkout (no activated org config). Replaced in `docs/eval_gates.md` with `python -m evals.run_phase5_benchmark`. Verified exit 0 on this host.

### F2 — No Phase 5 gate closure artifact
**Status:** **CONFIRMED** → **CLOSED by this document.**

### F3 — DEC-054 zero-evidence backstop untested
**Status:** **CONFIRMED** → **CLOSED.**

Added `tests/codification/test_sweep.py::test_zero_evidence_marker_stripped_still_rejected_by_preflight` — strips proposed markers, replaces `never_contain` sentinel, asserts `run_preflight` raises `invalid_snapshot` (Pydantic `min_length` on empty `assets_and_asset_groups.entries`). Dedicated `zero_evidence_not_activatable` code **not** added: incidental backstop is sufficient defense-in-depth; relaxing the model constraint remains the real risk (documented in DEC-054 row).

### F4 — Stale evidence counts
**Status:** **CONFIRMED** → **RECONCILED.**

Updated `.workflow/TASK-034/verification.md`, `.workflow/TASK-035/verification.md`, `memory-bank/{activeContext,tasks}.md` to **17** codification tests, **7** benchmark + **10** doc tests, suite **778**, mypy **118** files.

### F5 — Placeholder sentinel coverage asymmetry
**Status:** **CONFIRMED intentional** → **DOCUMENTED as DEC-057.**

`collect_sweep_placeholder_violations` scans only `subnet_membership` and `never_contain[].target_id`. Advisory prose in `business_context.notes` and `normal_admin_patterns[].description` is review-only, not activation-blocking — safety-critical topology fields only.

---

## Task 34 criteria (`docs/plan.md` lines 600–607) — verdicts

| Criterion | Verdict | Evidence |
|---|---|---|
| Sweep summarizes principals, assets, admin patterns, frequency counts | **PASS** | `test_sweep_summarizes_observations_from_fixtures` |
| Output is proposed artifact, not active config | **PASS** | `test_proposed_artifact_rejected_by_preflight`; `artifact_kind: proposed_org_config` |
| Report documents coverage limits and absence-of-evidence risks | **PASS** | `test_report_documents_coverage_limits`, `test_report_documents_absence_of_evidence_risks`, `test_report_telemetry_coverage_matches_normalizer_event_ids` |
| SOC lead can review before activation | **PASS** | `test_sweep_exposes_reviewable_artifact_and_report` |
| Preflight rejects proposed marker | **PASS** | `test_proposed_artifact_rejected_by_preflight` → `proposed_artifact_not_activatable` |
| Preflight rejects marker-stripped unreplaced sentinels | **PASS** | `test_marker_stripped_placeholder_artifact_rejected_by_preflight` → `unreplaced_sweep_placeholder` |
| Positive control: replaced config activates | **PASS** | `test_placeholders_replaced_artifact_passes_preflight` |
| Zero-evidence artifact unusable | **PASS** | `test_empty_telemetry_produces_unusable_zero_evidence_artifact` |
| Zero-evidence backstop when markers/sentinels stripped | **PASS** | `test_zero_evidence_marker_stripped_still_rejected_by_preflight` → `invalid_snapshot` |
| Empty/skipped/ambiguous telemetry edge cases | **PASS** | `test_all_skipped_telemetry_*`, `test_ambiguous_sysmon_user_*`, identity merge tests, per-host/per-user pattern uniqueness |
| Live SOC review of sweep output | **MANUAL** | Expected — artifact is for human review (TASK-034 verification skipped checks) |

---

## Task 35 criteria (`docs/plan.md` lines 609–624) — verdicts

| Criterion | Verdict | Evidence |
|---|---|---|
| Benchmark uses provisional sustained/burst targets from active org config | **PASS** | `test_serialized_path_benchmark_uses_active_org_config_targets` |
| DEC-053 production path: gate eval + deferred persist + ledger (no spurious revocation) | **PASS** | `test_production_path_transaction_structure` (2 `BEGIN IMMEDIATE`); `test_benchmark_iteration_write_set_uncontended` (ledger +2, outbox unchanged) |
| Contended-path suppression | **PASS** | `test_contended_path_suppresses_second_directive_emission` |
| Target comparison semantics + burst honestly labeled | **PASS** | `test_benchmark_target_comparison_semantics`; `burst_separately_measured=False` in module + tests |
| Throughput ceiling documented in runbook | **PASS** | `test_operator_runbook_documents_throughput_ceiling` |
| Runbook two-transaction claim matches benchmark | **PASS** | `test_operator_runbook_transaction_count_matches_benchmark` |
| Docs reference generated schemas | **PASS** | `test_architecture_references_schemas`, `test_generated_schema_index_files_exist` |
| Runbook required topics (LLM recovery, breakers, feed, JSONL, emergency race, etc.) | **PASS** | `test_operator_runbook_required_topics` (incl. JSONL no rotation machinery / segmented rotation deferred) |
| API docs use `standard_review`, not `pass` | **PASS** | `test_operator_runbook_rejects_pass_disposition` |
| Architecture + eval_gates phase documentation | **PASS** | `test_architecture_exists`, `test_eval_gates_documents_phase_gates` |
| Measured throughput vs example-org target (30/min sustained) | **PASS (hardware-dependent)** | `evals.run_phase5_benchmark`: **14402.3**/min, `meets_sustained_target=True`; `test_recorded_sample_run_meets_example_org_sustained_target` pins sample on temp DB |
| Plan "feed outbox insertion where applicable" | **PASS (scoped)** | Production benchmark excludes per-alert outbox per DEC-056; revocation/feed outbox measured separately by `benchmarks/smoke_serialized_path.py` (Phase 1 gate) — not re-run here |
| New operator can understand system without reading source | **PASS (doc coverage)** | Runbook + architecture content tests; **MANUAL** readability review not automated |

---

## Phase 5 pass criteria (`docs/eval_gates.md` + `docs/plan.md` Phase 5) — verdicts

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Empirical sweep generates reviewable proposed org-config artifact | **PASS** | Codification tests + preflight rejection suite |
| 2 | Production throughput ceiling measured and documented | **PASS** | `evals.run_phase5_benchmark` + `docs/operator_runbook.md` content tests |
| 3 | Operator runbook/architecture cover responsibility boundaries | **PASS** | `test_operator_runbook_required_topics`, architecture schema refs |
| 4 | Splunk Free demo executed end-to-end against live instance | **PASS-WITH-CONDITIONS (manual)** | `test_splunk_demo_manual_procedure_only` is env-gated skip (not unconditional skip); offline SPL matcher remains Phase 4 proof; live HEC path documented in `splunk/README.md` only |

---

## Load-bearing claims — incidental vs pinned validation

| Claim | Validation | Gap |
|---|---|---|
| DEC-053 two-transaction production path | Transaction count + write-set tests | None for Sprint 5 scope |
| Benchmark mirrors intake, not smoke revocation path | Module docstring + outbox unchanged assertion | Smoke path not re-gated here (Phase 1) |
| Zero-evidence cannot activate after marker strip | New regression test | Rejection code is generic `invalid_snapshot` (accepted) |
| Placeholder scan scope | DEC-057 documented | Advisory fields intentionally unscanned |
| Splunk demo reproducible-by-execution | Manual procedure test only | **Open:** live demo not executed in this gate run |
| SOC lead review of real sweep output | Manual | Expected |

---

## Phase 3/4 carry-forward (unchanged by Sprint 5)

| ID | Item | Status |
|---|---|---|
| T1–T4, T6 | Phase 3 policy/correlation hygiene | **OPEN** — out of Sprint 5 scope |
| T7 | Sigma↔SPL matcher equivalence pin | **OPEN** |
| REVIEW-004 | Correlator cross-host noise xfail | **OPEN** (1 xfailed) |

---

## GATE DECISION

**PASS-WITH-CONDITIONS**

**Rationale:** All automatable Sprint 5 deliverables pass on independently re-run mechanical checks. Sweep preflight is pinned (proposed marker, stripped sentinels, zero-evidence backstop, positive control). Production benchmark is self-contained, DEC-053-faithful, and clears example-org sustained target on this hardware (**14402.3** vs **30** alerts/min). Operator documentation coverage is test-pinned.

**Conditions (non-blocking for Sprint 5 code complete, blocking for “fully operator-verified” release):**

1. **Live Splunk demo:** Execute `splunk/README.md` end-to-end once against Splunk Free with HEC env vars set; record fixture `record_id` hits. CI remains manual/env-gated by design (`docs/eval_gates.md`).
2. **Live SOC review:** Human review of sweep proposed artifact on representative telemetry — manual gate outside pytest.

**Sprint 5 is complete as a release gate** for codification, preflight, throughput measurement, and operator documentation. Full repo-wide gate pass remains a separate exercise.
