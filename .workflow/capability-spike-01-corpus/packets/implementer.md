# Implementer packet — capability-spike-01-corpus

## Objective

Add labeled anchor manifest schema/loader for the judgment capability spike (balanced malicious/benign corpus).

## Original user goal

Load judgment capability spike into GSD and drain. This task is Task 1 of that plan.

## Relevant docs

- `docs/superpowers/plans/2026-08-01-judgment-capability-spike.md` — **Task 1** (follow steps/tests/code verbatim)
- `docs/superpowers/specs/2026-08-01-capability-spike-design.md`
- `.workflow/_dream/playbook.digest.md` (GR-0001, GR-0007)

## Allowed files (write only these)

- evals/capability/__init__.py
- evals/capability/corpus.py
- tests/evals/capability/__init__.py
- tests/evals/capability/test_corpus.py
- tests/evals/capability/fixtures/
- .workflow/capability-spike-01-corpus/

## Do not touch

- `src/praetor/**`
- `evals/harness.py`
- `evals/scenarios/**`
- `praetor.judgment.agentic` (never import)
- Any file outside files_allowed

## Acceptance criteria

- load_anchor_manifest loads valid YAML into frozen Anchor/AnchorManifest.
- Naive timestamps coerced to UTC; duplicate ids, unbalanced classes, invalid expected_class, and empty rationale raise ManifestError.
- Committed tests pass offline with FakeProvider-free fixtures.

## Implementation instructions

1. Implement Task 1 from the plan exactly: failing tests first, then `corpus.py` + fixtures as specified in the plan.
2. Run verification commands below until green.
3. Do **not** mark the queue item done.
4. Do **not** run phase/sprint exit verification.
5. Stop and report `approval_gates` before dependency installs, `.codex`/`.claude` edits, clones, or writes outside files_allowed.
6. Commit allowed files with the plan commit message if clean; if hooks fail, report rather than `--no-verify`.
7. Self-review against Global Constraints in the plan header.

## Verification commands

- `pytest tests/evals/capability/test_corpus.py -q`
- `ruff check evals/capability tests/evals/capability`
- `mypy evals/capability`

## Expected result schema

Write a short summary covering: files created/changed, commands run + exit codes, any blockers.
