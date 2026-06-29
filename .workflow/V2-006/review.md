# Review — V2-006

## REVIEW-001

**Scope:** DEC-058 rule-action blocking at policy layer.

**Findings:** None blocking.

- `escalate` and `deny` both block `auto_contain` with distinct fault flags per DEC-058.
- Unresolved permit+block conflict without precedence still emits `policy_ambiguity`.
- Example org `default_escalate` catch-all now correctly blocks containment; tests that need `auto_contain` use explicit permissive policy overrides (deferred full posture flip to V2-013).
- Provisional fault flag names wired in `OutcomeMatrixFaultFlag` + eval harness scenarios; `docs/contracts.md` §13 rows deferred (task constraint + DEC-058).

**Gap logged:** No-rule implicit ALLOW fallthrough remains until V2-013; `default_action` schema until V2-012.
