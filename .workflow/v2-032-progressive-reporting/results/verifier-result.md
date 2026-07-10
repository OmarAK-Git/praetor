# Verifier Result — V2-032 Progressive Authorization Reporting

**Role:** Adversarial skeptic-verifier. Implementer claims treated as unevidenced; all evidence gathered independently.
**Scope:** V2-032 acceptance criteria ONLY (V2 Gate 5 and unrelated gaps explicitly excluded).

## Overall: pass (with a documented follow-up gap)

All four V2-032 acceptance criteria pass under independent verification. One real regression is caused by this task's new package but its fix lies outside the task's allowed file set and was pre-disclosed by the implementer; it does not violate any of the four acceptance criteria.

---

## Commands run

### Specified verification command
```
python -m pytest tests/metrics/ tests/annotations/ -q
```
Output:
```
.......................................................                  [100%]
55 passed in 2.01s
```
Exit code: 0 — reproduced the implementer's claim independently.

### Adversarial regression probe (not requested, but caused by this task)
```
python -m pytest tests/contracts/test_scope_guard.py -q
```
Output:
```
.F.......                                                                [100%]
FAILED tests/contracts/test_scope_guard.py::test_only_expected_top_level_packages
E   AssertionError: package allowlist drift: unexpected={'reporting'}, missing=frozenset()
1 failed, 8 passed in 0.93s
```
Exit code: 1 — the new `src/praetor/reporting/` package trips the repo's own top-level package allowlist.

---

## Per-criterion verdict

### Criterion 1 — Aggregates PolicyGate override rate + annotation outcomes by (target_type, asset_class) over a window — PASS
- `build_progressive_authorization_report` (`src/praetor/reporting/progressive_authorization.py:59`) runs SELECT aggregation `GROUP BY target_type, asset_class` with `evaluated_at >= ? AND < ?` window bounds (lines 73-87).
- Override rate derived per dimension (`policy_gate_override_rate`, lines 19-23); `overridden` flag computed as `proposed != final` at record time (`evaluations.py:68`).
- Annotation outcomes joined `analyst_annotations ⋈ policy_gate_evaluations ON decision_id`, windowed on annotation `$.timestamp`, with correct/incorrect and corrected-disposition breakdown (lines 99-131).
- Evidence: `test_aggregates_policy_gate_override_rate_by_dimension` (override rate 0.5/0.0 across host+account dims), `test_aggregates_annotation_outcomes_by_dimension` (2 annotations, 1 correct/1 incorrect, `{"standard_review": 1}`), `test_excludes_evaluations_outside_window` (window filter). Tests exercise the real code path and assertions are not weakened. All pass.

### Criterion 2 — Read-only decision support; no self-tuning / auto config promotion — PASS
- Reporting module imports only `sqlite3`, `dataclass`, `datetime` — no config-activation, no write paths. All DB access is `conn.execute(SELECT ...)`.
- `read_only`/`PROGRESSIVE_AUTHORIZATION_REPORT_READ_ONLY` is a constant `True` (lines 9, 50).
- Evidence: `test_report_builder_is_read_only` snapshots row counts of `policy_gate_evaluations`, `analyst_annotations`, and `ledger_chain` before/after and asserts equality (unchanged) — a genuine mutation check, not a symbolic flag check. Passes.

### Criterion 3 — Runbook documents SOC-led promotion/reversal workflow — PASS
- `docs/operator_runbook.md:250-299` "Progressive authorization reporting (read-only)" section covers: what the report measures, generation example, a 5-step SOC-led promotion workflow (review → deliberate → propose → activate via `activate_org_config` audited path → record rationale), an explicit reversal path ("same path in reverse", never automatic), and explicit non-goals ("no self-tuning, automatic config promotion, or statute mutation").

### Criterion 4 — Verifier checks only V2-032 acceptance — PASS
- Confined verification to the four criteria; V2 Gate 5 and unrelated backlog not assessed.

---

## Gaps / risks

1. **Regression — scope-guard suite is red (caused by this task).** Adding `src/praetor/reporting/` breaks `tests/contracts/test_scope_guard.py::test_only_expected_top_level_packages`. This is a direct, reproducible side effect of V2-032, not a pre-existing or unrelated failure. It does not violate any of the four acceptance criteria, and the fix (adding `reporting` to `ALLOWED_PACKAGES`) requires editing `tests/contracts/`, which the implementer states is outside V2-032's allowed file set. Pre-disclosed in implementer result (deferred item #1). **Action required in a follow-up task before the full suite can be green.**

2. **Not wired end-to-end (functionality exists but is dormant in production).** Per implementer deferred items #2 and #3, verified against code:
   - `open_state_store` does not call `init_policy_gate_evaluation_schema`, so the `policy_gate_evaluations` table is not created in production state (tests init it explicitly in the fixture).
   - The orchestrator/engine intake never calls `record_policy_gate_evaluation`, so no rows are produced in production.
   - Consequence: today the report would return empty dimensions against a real production DB. The aggregation *contract* is proven by tests, but the reporting view is not yet fed by live data. Acceptance criteria (which describe the reporting view capability) are met; operational usefulness depends on the deferred wiring tasks.

## Anti-gaming checks performed
- Confirmed the specified verification command's 55 passing tests include the new V2-032 tests and that those tests import and call `build_progressive_authorization_report` / `record_policy_gate_evaluation` (real code, not stubs).
- Confirmed the read-only test asserts actual row-count invariance, not just the `read_only` boolean.
- Confirmed annotation join field names (`$.disposition_correct`, `$.corrected_disposition`, `$.timestamp`) match the persisted `AnalystAnnotation` serialization; the aggregation test's positive/negative/corrected assertions pass, so the JSON extraction is exercised and correct.
- Independently reproduced both the passing suite and the scope-guard failure.
