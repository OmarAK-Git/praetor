# Implementer packet — eval-kernel-01-scorecard

## Objective

Task 1 — Scorecard schema + Pydantic model: ScorecardRow with extra=forbid, pending legal only for capability quality new_build, failure_class none on pass/pending and required on fail/error.

## Original user goal

Check PR 1 and 2 (eval-kernel spec + Sprint 1 plan), accept them, load GSD, drain the loop. This is Task 1 of Sprint 1.

## Relevant docs

- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` — **Task 1** (follow steps/tests/code verbatim)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §4 scorecard table
- `.workflow/_dream/playbook.digest.md` (GR-0001)

## Allowed files (write only these)

- evals/schemas/scorecard_schema.json
- evals/scorecard.py
- tests/evals/test_scorecard.py
- .workflow/eval-kernel-01-scorecard/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

## Do not touch

- `src/praetor/**`
- `evals/harness.py`
- `evals/scenarios/**`
- Any CBC adapter / AlertEnvelope / EventID work
- Any file outside files_allowed

## Acceptance criteria

- scorecard_schema.json has additionalProperties false and the spec §4 required fields.
- ScorecardRow rejects unknown fields.
- pending is legal only for cap.baseline_bag_path_a and cap.stump_parity_guard new_build.
- pending is illegal for cap.no_label_leak_ids and non-capability rows.
- failure_class is none when pass or pending, and not none when fail or error.
- The verifier checks only Task 1 acceptance, not Sprint 1 gate completion.

## Implementation instructions

1. Implement Task 1 from the plan exactly: failing tests first, then schema + `evals/scorecard.py` as specified.
2. Run verification commands below until green.
3. Do **not** mark the queue item done.
4. Do **not** run phase/sprint exit verification.
5. Stop and report `approval_gates` before dependency installs, `.codex`/`.claude` edits, clones, or writes outside files_allowed.
6. Commit allowed files with the plan commit message (`feat(evals): add E2E scorecard schema and pending rules`) if clean; if hooks fail, report rather than `--no-verify`. Push the current branch after a successful commit.
7. Self-review against Global Constraints in the plan header.

## Verification commands

- `pytest tests/evals/test_scorecard.py -q`
- `ruff check evals/scorecard.py tests/evals/test_scorecard.py`
- `mypy evals/scorecard.py`

## Expected result schema

Write a short summary covering: files created/changed, commands run + exit codes, any blockers. Do not claim the queue item is done.
