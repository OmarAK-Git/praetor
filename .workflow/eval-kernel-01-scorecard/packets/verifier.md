# Verifier packet — eval-kernel-01-scorecard

Treat implementer claims as unevidenced until you re-run the commands.

Ignore phase-level or sprint-level gaps. verification.scope is task.

## Original user goal

Task 1 — Scorecard schema + Pydantic model.

## Acceptance criteria

- scorecard_schema.json has additionalProperties false and the spec §4 required fields.
- ScorecardRow rejects unknown fields.
- pending is legal only for cap.baseline_bag_path_a and cap.stump_parity_guard new_build.
- pending is illegal for cap.no_label_leak_ids and non-capability rows.
- failure_class is none when pass or pending, and not none when fail or error.
- The verifier checks only Task 1 acceptance, not Sprint 1 gate completion.

## Changed files

- evals/schemas/scorecard_schema.json
- evals/scorecard.py
- tests/evals/test_scorecard.py

## Verification commands (run these yourself)

- pytest tests/evals/test_scorecard.py -q
- ruff check evals/scorecard.py tests/evals/test_scorecard.py
- mypy evals/scorecard.py

## Manual checks

- No src/praetor/ edits.
- No evals/harness.py edits.

## Implementer result path (unevidenced)

.workflow/eval-kernel-01-scorecard/results/implementer-result.md

Write verdict to .workflow/eval-kernel-01-scorecard/results/verifier-result.md
Outcome: pass | gaps | human_needed
Include command output summaries and exit codes you actually observed.
