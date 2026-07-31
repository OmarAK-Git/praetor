# Verifier packet — agentic-judgment-02-registry

## Goal
Add session_trace hash domain and SessionEvidenceRegistry.

## Acceptance criteria
- compute_session_trace_hash is deterministic, content-sensitive, and returns 64-hex for empty sessions.
- SessionEvidenceRegistry records evidence/org-config/exemplar entries and exposes facts/exemplars/org_config_findings plus session_trace_hash().
- DOMAIN_SESSION_TRACE lives in hashing/domains.py only (AG-0007).

## Changed files
- src/praetor/hashing/domains.py
- src/praetor/judgment/agentic/__init__.py
- src/praetor/judgment/agentic/registry.py
- tests/hashing/test_domains.py
- tests/judgment/agentic/__init__.py
- tests/judgment/agentic/test_registry.py

## Commands (PYTHONPATH=worktree/src)
- pytest tests/hashing/test_domains.py tests/judgment/agentic/test_registry.py -v
- ruff check src/praetor/hashing/domains.py src/praetor/judgment/agentic tests/hashing/test_domains.py tests/judgment/agentic
- mypy src/praetor/hashing/domains.py src/praetor/judgment/agentic

## Implementer result
`.workflow/agentic-judgment-02-registry/results/implementer-result.md`

Treat claims as unevidenced until checked. Ignore phase-level gaps. Write verifier-result.md.
