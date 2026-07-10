# Verification Ledger — Autopilot Loop Setup

| ID | Requirement | Command | Result | Status |
| --- | --- | --- | --- | --- |
| VERIFY-AUTO-001 | Queue JSON parses | `python -m json.tool .workflow/autopilot-queue.json` | pending | pending |
| VERIFY-AUTO-002 | Command wiring | `rg "autopilot-queue\|autopilot-loop/state" .cursor/commands/gsd-autopilot-loop.md` | pending | pending |
| VERIFY-AUTO-003 | Task-scoped default | inspect `defaults.verification_scope` in queue | pending | pending |
| VERIFY-AUTO-004 | Explicit gate item | `v2-gate-2-exit` has `verification.scope: phase_exit` | pending | pending |
