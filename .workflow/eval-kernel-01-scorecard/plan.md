# eval-kernel-01-scorecard

**Goal:** Task 1 — Scorecard schema + Pydantic model: ScorecardRow with extra=forbid, pending legal only for capability quality new_build, failure_class none on pass/pending and required on fail/error.

**Scope:** Scorecard schema and validator only. Do not add kernel runner, scenarios, or CI. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- scorecard_schema.json has additionalProperties false and the spec §4 required fields.
- ScorecardRow rejects unknown fields.
- pending is legal only for cap.baseline_bag_path_a and cap.stump_parity_guard new_build.
- pending is illegal for cap.no_label_leak_ids and non-capability rows.
- failure_class is none when pass or pending, and not none when fail or error.
- The verifier checks only Task 1 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/schemas/scorecard_schema.json
- evals/scorecard.py
- tests/evals/test_scorecard.py
- .workflow/eval-kernel-01-scorecard/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/test_scorecard.py -q
- ruff check evals/scorecard.py tests/evals/test_scorecard.py
- mypy evals/scorecard.py
