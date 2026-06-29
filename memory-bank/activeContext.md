# Active Context

## Current focus

**V2-009 complete** on branch `task/V2-009` in worktree `.worktrees/V2-009`.

**Sprint V2-1 (Safety-Critical V1 Gap Closure):** V2-005 and V2-009 complete. V2-006 (in progress on main), V2-007–V2-010 remain for Gate 1.

## Recently changed

- V2-009: PolicyGate live never-contain authorization wired through `emergency.py`; engine-intake harness emergency setup; `emergency_never_contain_intake.yaml` scenario.

## Current blockers

- **V2 Gate 1** — V2-006/V2-007/V2-008/V2-010 still open on main.
- REVIEW-004 correlator cross-host xfail → V2-014.

## Important notes for agents

1. V2-009 work lives in worktree `.worktrees/V2-009` (branch `task/V2-009`).
2. Intake: DEC-053 deferred directive persist unchanged.
3. Revocation ledger append: all automated paths use `automated_revoke_directive_in_transaction` (activation, emergency, recovery).
