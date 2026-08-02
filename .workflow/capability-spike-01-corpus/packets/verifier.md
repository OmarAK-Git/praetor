# Verifier packet — capability-spike-01-corpus

## Goal

Add labeled anchor manifest schema/loader for the judgment capability spike (balanced malicious/benign corpus).

## Acceptance criteria

- load_anchor_manifest loads valid YAML into frozen Anchor/AnchorManifest.
- Naive timestamps coerced to UTC; duplicate ids, unbalanced classes, invalid expected_class, and empty rationale raise ManifestError.
- Committed tests pass offline with FakeProvider-free fixtures.

## Changed files (commit 1891684)

- evals/capability/__init__.py
- evals/capability/corpus.py
- tests/evals/capability/__init__.py
- tests/evals/capability/fixtures/manifest_valid.yaml
- tests/evals/capability/test_corpus.py

## Verification commands

- `pytest tests/evals/capability/test_corpus.py -q`
- `ruff check evals/capability tests/evals/capability`
- `mypy evals/capability`

## Manual checks

- No imports from praetor.judgment.agentic.
- Nothing in evals/capability is imported by evals/harness.py.
- No src/praetor/ edits.

## Implementer result path

`.workflow/capability-spike-01-corpus/results/implementer-result.md`

## Instructions

- Treat implementer claims as unevidenced until you re-check.
- Ignore phase-level or sprint-level gaps (verification.scope is task).
- Write verdict to `.workflow/capability-spike-01-corpus/results/verifier-result.md` with PASS or FAIL and evidence.
