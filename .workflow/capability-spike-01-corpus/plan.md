# capability-spike-01-corpus

## Goal

Add labeled anchor manifest schema/loader for the judgment capability spike (balanced malicious/benign corpus).

## Scope

evals/capability corpus loader + unit tests/fixtures only; no src/praetor changes; no evals/harness.py changes.

## Tier

T2

## Allowed files

- evals/capability/__init__.py
- evals/capability/corpus.py
- tests/evals/capability/__init__.py
- tests/evals/capability/test_corpus.py
- tests/evals/capability/fixtures/
- .workflow/capability-spike-01-corpus/

## Acceptance criteria

- load_anchor_manifest loads valid YAML into frozen Anchor/AnchorManifest.
- Naive timestamps coerced to UTC; duplicate ids, unbalanced classes, invalid expected_class, and empty rationale raise ManifestError.
- Committed tests pass offline with FakeProvider-free fixtures.

## Verification commands

- `pytest tests/evals/capability/test_corpus.py -q`
- `ruff check evals/capability tests/evals/capability`
- `mypy evals/capability`

## Manual checks

- No imports from praetor.judgment.agentic.
- Nothing in evals/capability is imported by evals/harness.py.
- No src/praetor/ edits.

## Sources

- Plan: docs/superpowers/plans/2026-08-01-judgment-capability-spike.md (Task 1)
- Spec: docs/superpowers/specs/2026-08-01-capability-spike-design.md
