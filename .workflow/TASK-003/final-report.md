# Final report: TASK-003

## Summary

TASK-003 delivered canonical serialization and hash domain constants per `docs/contracts.md`. A pre-commit human review corrected two contract gaps **doc-first**: new §5 `stamp_id` (three-tuple, stable across attempts) and §7 `EMPTY_BUNDLE` preimage ratification. Implementation in `src/praetor/hashing/` matches the updated authoritative doc.

## Files changed

| Path | Change |
|------|--------|
| `docs/contracts.md` | §5 `stamp_id`; §7 `EMPTY_BUNDLE` preimage; renumber §6–§15 |
| `src/praetor/hashing/canonical.py` | Canonical serialize/hash; `EMPTY_BUNDLE` from §7 preimage |
| `src/praetor/hashing/domains.py` | Domain constants; derivations including §5 `stamp_id` |
| `src/praetor/hashing/__init__.py` | Public exports |
| `tests/hashing/test_canonical.py` | Task 3 criteria + stamp stability + preimage test |
| `tests/contracts/test_scope_guard.py` | Allow `hashing`; docs changes limited to `contracts.md` |
| `.workflow/TASK-003/*` | Plan, traceability, verification, review, state |
| `memory-bank/*` | Updated for contracts.md § renumber and resolved gaps |

## Checks

| Check | Result |
|-------|--------|
| `pip install -e ".[dev]"` | pass |
| `pytest -q` | pass (62 tests) |
| Domain literal grep | pass — only `domains.py` for §2 constants |
| `docs/contracts.md` authoritative for `stamp_id` + `EMPTY_BUNDLE` | pass |
| Import `praetor.hashing` | pass |

## Gaps / skipped checks

- Cross-Python/Pydantic patch determinism pin not exercised beyond current environment
- CI, ruff, mypy

## Follow-up

| Item | Owner | Notes |
|------|-------|-------|
| TASK-004 | next agent | Authenticated write surface primitives |
| Align `docs/spec.md` cross-refs | optional | May still cite old § numbers; contracts.md is SSOT |

## Sign-off

- **Run status:** complete (post human review)
- **Evidence fresh as of:** 2026-06-01
