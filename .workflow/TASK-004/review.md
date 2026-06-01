# Review: TASK-004

## Review findings

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| R-001 | note | Token wire format not specified in authoritative docs | Pluggable `TokenVerifier` protocol; `PrincipalMapVerifier` for tests only |
| R-002 | note | No HTTP/API layer in Task 4 | Surfaces are Python callables; HTTP binding deferred to future tasks |

**Severity:** `blocker` | `major` | `minor` | `note`

## Risks (post-review)

| Risk | Status |
|------|--------|
| Operator IdP must implement `TokenVerifier` | accepted — by design per `docs/spec.md` |
| Internal ops rely on convention until Tasks 5–10 wire enforcement | accepted — `InternalOperation` enum documents boundary |

## Human review notes

- **Reviewer:** agent
- **Date:** 2026-06-01
- **Decision:** approve

## Open items

- None blocking TASK-005
