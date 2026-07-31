# agentic-judgment-02-registry

## Goal
Add session_trace hash domain and SessionEvidenceRegistry.

## Scope
Hash domain + agentic registry package scaffolding only.

## Acceptance criteria
- compute_session_trace_hash is deterministic, content-sensitive, and returns 64-hex for empty sessions.
- SessionEvidenceRegistry records evidence/org-config/exemplar entries and exposes facts/exemplars/org_config_findings plus session_trace_hash().
- DOMAIN_SESSION_TRACE lives in hashing/domains.py only (AG-0007).

## Files allowed
- src/praetor/hashing/domains.py
- src/praetor/judgment/agentic/
- tests/hashing/test_domains.py
- tests/judgment/agentic/
- .workflow/agentic-judgment-02-registry/
- docs/contracts.md

## Verification
- `pytest tests/hashing/test_domains.py tests/judgment/agentic/test_registry.py -v`
- `ruff check src/praetor/hashing/domains.py src/praetor/judgment/agentic tests/hashing/test_domains.py tests/judgment/agentic`
- `mypy src/praetor/hashing/domains.py src/praetor/judgment/agentic`

## Tier
T2

## Researcher decision
skipped: single prescribed implementation path in plan; no multi-path opportunity cost

## Standing orders
- TDD: failing test first, then implement
- Do NOT commit
- Do NOT install dependencies
- Worktree root: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`
- Set `PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src` for all python/pytest/mypy
- Single-shot provider / PolicyGate evaluation logic untouched
