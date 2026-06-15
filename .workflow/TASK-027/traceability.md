# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001 | TASK-027 | `build_adversarial_evidence_facts()` | `test_adversarial_facts_*` | REVIEW-001 | pending |
| REQ-002 | AC-001 | DEC-002 | TASK-027 | `assert_structural_preconditions()` | `test_structural_preconditions_*` | REVIEW-002 | pending |
| REQ-003 | AC-001 | DEC-003 | TASK-027 | `GeminiJudgmentProvider`, env gate | `test_probe_skipped_without_credentials` | REVIEW-003 | pending |
| REQ-004 | AC-001 | DEC-004 | TASK-027 | pytest markers on integration test | `test_probabilistic_test_has_required_markers` | REVIEW-004 | pending |
| REQ-005 | AC-002 | DEC-005 | TASK-027 | log-only integration test; `addopts` exclusion | default `pytest -q` | REVIEW-005 | pending |
| REQ-006 | AC-001 | DEC-006 | TASK-027 | module docstring | manual review | REVIEW-006 | pending |

## Decisions

- **DEC-001:** Adversarial text lives in `normalized_fields.command_line` so it passes excerpt sanitization but remains provider-visible — mirrors log-injection threat model.
- **DEC-002:** Structural checks reuse Task 14 excerpt/prompt builders; only pre-provider invariants are asserted deterministically.
- **DEC-003:** Optional Gemini REST in `evals/` keeps `src/` Vertex stub unchanged; probe enabled only via `PRAETOR_REAL_PROVIDER_PROBE=1`.
- **DEC-004:** Both `integration` and `probabilistic` markers required per plan.md.
- **DEC-005:** Default pytest excludes both markers; probabilistic test never asserts model outcome.
- **DEC-006:** `docs/` edit blocked; structural vs probabilistic distinction in module docstring + flight recorder.
