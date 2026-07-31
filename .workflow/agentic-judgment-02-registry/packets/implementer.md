# Implementer packet — agentic-judgment-02-registry

## Objective
Add session_trace hash domain and SessionEvidenceRegistry.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/hashing/domains.py
- src/praetor/judgment/agentic/
- tests/hashing/test_domains.py
- tests/judgment/agentic/
- .workflow/agentic-judgment-02-registry/
- docs/contracts.md

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- compute_session_trace_hash is deterministic, content-sensitive, and returns 64-hex for empty sessions.
- SessionEvidenceRegistry records evidence/org-config/exemplar entries and exposes facts/exemplars/org_config_findings plus session_trace_hash().
- DOMAIN_SESSION_TRACE lives in hashing/domains.py only (AG-0007).

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/hashing/test_domains.py tests/judgment/agentic/test_registry.py -v`
- `ruff check src/praetor/hashing/domains.py src/praetor/judgment/agentic tests/hashing/test_domains.py tests/judgment/agentic`
- `mypy src/praetor/hashing/domains.py src/praetor/judgment/agentic`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
