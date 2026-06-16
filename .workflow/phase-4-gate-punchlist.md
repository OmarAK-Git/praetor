# Phase 4 gate — consolidated punch-list

**Date:** 2026-06-16  
**Scope:** Tasks 32, 33 (detection portability sprint)  
**Sources merged:** independent gate-wide verification (mechanical re-run + code/doc audit), TASK-033 hardening review (correlation rejection, modifier preflight, props, savedsearch dedup), and the post-hardening evidence reconciliation.  
**Gate decision:** **CLEARED AS PASS-WITH-CONDITIONS 2026-06-16** — all four Phase 4 pass criteria (`docs/plan.md:646`) are met on fresh evidence (744 passed, 2 deselected, 1 xfailed; mypy 112 files; ruff clean incl. `tools`; `compile_sigma.py --check` exit 0; 39 detection+splunk tests). Portability is verified **without Splunk** by an offline SPL-vs-fixture matcher with positive + discrimination assertions. Residual items are non-blocking: an unpinned Sigma↔SPL matcher-equivalence invariant, the live-Splunk HEC path (operator-driven by design), and Phase 3 hygiene carry-forwards untouched by the detection sprint.

> Unlike Phase 2 (F1 was an active production-path gap), Phase 4 ships portable detection content plus a reproducible demo. The conditional pass here is for one coverage pin and accepted demo-layer deferrals — not for safety-critical incompleteness.

---

## Verification actually run (not self-reported)

| Check | Command | Result |
|---|---|---|
| Detection + Splunk tests | `python -m pytest -q tests/detections/test_sigma_rules.py tests/splunk/test_savedsearch_generation.py` | **39 passed, 1 deselected** |
| Splunk module alone | `python -m pytest -q tests/splunk/test_savedsearch_generation.py` | **21 passed, 1 deselected** |
| Compiler determinism | `python tools/compile_sigma.py --check` | **exit 0** (committed `.spl` + `savedsearches.conf` byte-match compiler) |
| Full suite | `python -m pytest -q -rx` | **744 passed, 2 deselected, 1 xfailed** (REVIEW-004 strict xfail — not XPASS) |
| Types | `python -m mypy src evals consumer_sdk` | **clean, 112 source files** |
| Lint | `python -m ruff check src tests evals consumer_sdk tools` | **clean** |
| Independent SPL match audit | offline re-derivation of `matching_record_ids` per committed `.spl` over manifest fixtures | **exact match** to `SPL_SEMANTIC_EXPECTATIONS` |

The green suite is necessary but not sufficient: the offline matcher independently reproduces every per-rule match set (powershell→{1002}, cmd→{1001,1005,1006}, calc→{9999}, notepad→{1003,1004}, 4624→{2001}), so the portability claim is evaluated against external fixture data, not the compiler's own output.

---

## Phase 4 gate criteria (`docs/plan.md:646`) — verdicts

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Sigma validates | **PASS** | `tests/detections/test_sigma_rules.py::test_sigma_rules_parse_without_errors`, `::test_sigma_rules_validate_without_blocking_issues` (pySigma core validators; HIGH+MEDIUM gated, stylistic logsource excluded), `::test_sigma_rules_compile_via_textquery_backend` |
| 2 | ATT&CK mapping present | **PASS** | `detections/attack_mapping.yaml` (5 rules); `::test_attack_mapping_covers_every_rule_file`, `::test_attack_mapping_entries_have_techniques`, `::test_attack_tags_match_mapping` (tag↔mapping technique+tactic parity), `::test_sigma_rules_have_attack_tags` |
| 3 | SPL generation deterministic | **PASS** | `python tools/compile_sigma.py --check` exit 0; `tests/splunk/...::test_spl_queries_are_deterministic`, `::test_committed_spl_matches_compiler`, `::test_compile_check_cli_passes`; `--write` rewrites byte-identical artifacts (guarded by `--check`) |
| 4 | Splunk demo reproducible w/ checksum-verified fixtures | **PASS** | `::test_fixture_manifest_checksums_python_mirror`; PowerShell `::test_ingest_script_validate_only` + `::test_ingest_script_validates_manifest_fixture_count` (PS count == YAML count) + `::test_ingest_script_fails_on_checksum_tamper` (fail-closed); offline portability `::test_committed_spl_semantic_match_and_discrimination`; `splunk/README.md` reproducible operator steps |

---

## Reviewer findings — confirm / refute

### F-1 (Process): no Phase 4 gate artifact
**Status:** **CONFIRMED** → **CLOSED by this document.**

Phases 1–3 each shipped a consolidated punch-list (`.workflow/phase-{1,2,3}-gate-punchlist.md`); Phase 4 had none. This punch-list is the Phase 4 gate artifact. An optional thin `evals/run_phase4_gate.py` (shelling the two pytest modules + `--check`) is tracked (T8) but not required — the criteria are fully covered by the table above.

---

### F-2 (Medium / docs): committed evidence under-reported coverage
**Status:** **CONFIRMED** → **RECONCILED.**

`abaa724` committed the hardened code (21 splunk tests, new `tools/spl_match.py`, `fixture_events.py`, `splunk_conf.py`) alongside **stale** evidence that still read "13 splunk tests / 736 passed" and listed already-closed gaps. Reconciled in the working tree:
- `.workflow/TASK-033/verification.md` — VERIFY-001 13→**21**, VERIFY-003 736→**744**.
- `.workflow/TASK-033/final-report.md` — counts updated; added **Resolved gaps (abaa724 hardening)**; stale correlation/dedup "known gaps" removed (only live-HEC remains).
- `memory-bank/{activeContext,progress,tasks}.md` — 736→**744**, 13→**21** with hardening notes (both `tasks.md` rows).

Numbers re-verified true (744 suite / 21 splunk). **Open sub-item:** the reconciliation is uncommitted — commit before declaring the gate durably closed.

---

### F-3 (Minor): Sigma↔SPL matcher equivalence not pinned
**Status:** **CONFIRMED** — no test asserts the invariant.

Two independent matchers exist — `tests/detections/test_sigma_rules.py::_event_matches_rule` (Sigma-level) and `tools/spl_match.py::matching_record_ids` (compiled-SPL level). Both anchor to hand-written expected record-id constants that agree, but nothing asserts *Sigma-match-set == SPL-match-set per rule over the manifest*. A pySigma bump within the `pysigma-backend-splunk>=1.1,<3` range could silently diverge them with both suites green.

**Disposition:** TRACK into Sprint 5 (T7). Low risk now — `--check` pins the SPL bytes, and the offline matcher pins SPL semantics against fixtures.

---

### F-4 (Accepted): live Splunk path never executed by an automated test
**Status:** **CONFIRMED** → **ACCEPT-AS-DEFERRED.**

`::test_splunk_demo_integration_skips_without_hec` skips unconditionally; `Send-SplunkEvents` and the PowerShell→Python flatten bridge in `tools/splunk_ingest_demo.ps1` run only under live HEC. Per `docs/spec.md:351` Splunk Free is a demo layer and the demo is operator-driven (`splunk/README.md`). Portability rests on the offline `tools/spl_match.py` matcher; its Splunk approximations (case-folding, leading-`*` endswith/contains, `\\`→`\` unescape) were audited as faithful for the v1 rule set. The flatten transform has one canonical implementation (`tools/fixture_events.py`) that the PowerShell path delegates to, so producer/consumer cannot drift.

---

### F-5 (Note): demo-layer minutiae
**Status:** **CONFIRMED** — non-blocking.

- `splunk/savedsearches.conf` `[default] dispatch.earliest_time = -30d` is a relative window that will eventually stop covering the 2026-06-08 fixtures (TRACK T9).
- `tools/` is outside the mypy gate (`src evals consumer_sdk`); `tools/compile_sigma.py` has 4 pysigma untyped-export / `SigmaCollection` invariance errors that no gate catches (TRACK T10). ruff *does* cover `tools` and is clean.

---

## TASK-033 hardening — confirmed closed (prior gatekeeper review)

| Gap | Closure | Evidence |
|---|---|---|
| Correlation-rule rejection untested | Two fixture tests, both raise sites | `::test_correlation_rule_rejected_by_validate_rule_supported`, `::test_correlation_rule_rejected_by_load_sigma_collection` |
| Modifier preflight blind to list-form + modifier chains | `_iter_selection_field_keys` walks lists; full chain checked | `::test_unsupported_list_form_modifier_raises_clear_error`, `::test_unsupported_chained_modifier_raises_clear_error` |
| `props.conf` inert / no validity check | Stanza parse + README HEC caveat | `::test_props_conf_parses_as_splunk_stanzas` |
| savedsearch double `source=` dismissed as cosmetic | Equivalence pin after dedup | `::test_savedsearch_query_matches_per_rule_spl_after_source_dedup` + `collapse_duplicate_source_terms` |
| No Splunk-free SPL semantics test | Offline matcher + discrimination | `::test_committed_spl_semantic_match_and_discrimination` |
| Dual manifest parser fail-open | PS count == YAML count | `::test_ingest_script_validates_manifest_fixture_count` |

---

## Phase 3 carry-forward (TRACK from `.workflow/phase-3-gate-punchlist.md`) — status

| ID | Item | Status after Sprint 4 |
|---|---|---|
| T1 | Static guard: policy fault-flag literals ⊆ `OutcomeMatrixFaultFlag` | **OPEN** — only transitive coverage (`tests/evals`, `tests/metrics`); out of detection scope → re-track |
| T2 | Production store asserts five policy tables under held singleton | **OPEN** — re-track (out of scope) |
| T3 | REVIEW-004 correlator cross-host in-window noise | **OPEN** — strict xfail still present (1 xfailed confirmed) |
| T4 | Optional `engine_intake` rate-counter eval | **OPEN** — re-track |
| T5 | Widen `tests/contracts/test_scope_guard.py` allowlist for Phase 5 docs | **OPEN — now imminent** — still `{contracts, plan, decisions}`; Task 35 adds `operator_runbook.md`, `architecture.md`, `eval_gates.md` → must widen before they land |
| T6 | Optional rename `resolve_host_target` → legacy | **OPEN** — note only |

None are Phase 4 blockers; the detection sprint did not touch policy/correlation/docs surfaces.

---

## TRACK — carry into Sprint 5

| ID | Item | Severity |
|---|---|---|
| T7 | Pin Sigma↔SPL equivalence: per rule, Sigma matcher set == SPL matcher set over manifest (F-3) | Minor |
| T8 | Optional `evals/run_phase4_gate.py` (two modules + `--check`) for single-command parity (F-1) | Note |
| T9 | Replace `dispatch.earliest_time = -30d` with a fixture-stable window, or document the demo time-range step (F-5) | Note |
| T10 | Decide whether `tools/` enters the mypy gate (or document the exclusion) (F-5) | Note |
| T1–T6 | Phase 3 carry-forwards above (T5 scope-guard widening is the most time-sensitive — needed for Task 35) | Minor/Note |

---

## ACCEPT-AS-DEFERRED

| Item | Basis |
|---|---|
| Live Splunk HEC ingest not exercised in CI | Demo layer per `docs/spec.md:351`; operator-driven (`splunk/README.md`); offline matcher backstops semantics |
| `props.conf` inert on the HEC path (sourcetype `_json` overrides) | Documented in `splunk/README.md`; applies to file/monitor ingest; parse test guards validity |
| PowerShell→Python flatten bridge runs only under live HEC | Logic centralized in `tools/fixture_events.py`, which the offline tests exercise |

---

## GATE DECISION

**PASS-WITH-CONDITIONS**

**Rationale:** All four Phase 4 gate criteria pass on independently re-run mechanical checks, and the load-bearing portability guarantee is verified offline against committed fixtures with positive + discrimination assertions. No safety-critical incompleteness. Conditions are non-blocking:

1. **F-2 commit:** commit the evidence reconciliation (working tree `M` on `.workflow/TASK-033/*` + `memory-bank/*`) so the corrected numbers are durable.
2. **T7 (F-3):** pin the Sigma↔SPL match-set equivalence invariant in Sprint 5.
3. **T5 (Phase 3 carry):** widen the scope-guard allowlist before Task 35 operator docs land.
4. **T8/T9/T10:** optional parity/hygiene notes.

**Sprint 5 may start** (Task 34 — Empirical Org-Config Sweep Prototype; depends on Tasks 9, 28, 30 — all complete — not on Sprint 4). Task 35 (production benchmark + runbooks) depends on all target-release tasks and must not close until conditions 1–3 are resolved.
