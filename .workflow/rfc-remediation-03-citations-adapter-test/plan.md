# RFC Remediation 03 — Citations Adapter Test

Goal: Add direct unit coverage for the `engine.citations` adapter without changing production citation behavior.

Allowed file: `tests/engine/test_citations.py`.

Acceptance criteria:
1. A resolvable citation returns true through the adapter.
2. Missing evidence IDs and missing field paths return false.
3. No production code changes.

Verification:
- `pytest tests/engine/test_citations.py -v`
- `ruff check .`
- `mypy .`

Source plan: `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md`, Task 3.

Research decision: no researcher dispatch; this is direct coverage of an existing 15-line adapter.
