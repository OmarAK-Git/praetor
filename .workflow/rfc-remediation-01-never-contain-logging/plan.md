# RFC Remediation 01 — Never-Contain Logging

Goal: Log malformed never-contain entries on both defensive matcher skip branches without changing matching or authorization outcomes.

Scope: RFC-003 observability only. Preserve skip-and-continue semantics, matching results, PolicyGate outcomes, disposition semantics, DEC-053 stamp ordering, and the existing never-contain production validation path.

Allowed implementation files:
- `src/praetor/config/live.py`
- `tests/config/test_live_never_contain_matching.py`

Acceptance criteria:
1. Both malformed-entry branches emit a warning through `praetor.config.live`.
2. Valid entries emit no warning and matching behavior remains unchanged.
3. No disposition, authorization, or never-contain semantics change.

Verification:
- `pytest tests/config/test_live_never_contain_matching.py -v`
- `ruff check .`
- `mypy .`

Source plan: `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md`, Task 1.

Research decision: no researcher dispatch; the approved plan prescribes one additive logging path with no viable design fork.
