# RFC Remediation 04 — Precedent Logging

Goal: Log malformed ledger edicts skipped during human-confirmed precedent fetch.

Allowed files:
- `src/praetor/annotations/precedent.py`
- `tests/annotations/test_precedent.py`

Acceptance:
1. A malformed edict is skipped with a warning containing its decision ID.
2. Existing similar-case retrieval remains unchanged.
3. No ranking, PolicyGate, or authorization behavior changes.

Verification:
- `pytest tests/annotations/test_precedent.py tests/judgment/test_similar_case_retrieval.py -v`
- `ruff check .`
- `mypy .`

Source plan: Task 4 of the reverse-spec RFC remediation plan.

Research decision: no researcher dispatch; this is one prescribed warning on an existing exception branch.
