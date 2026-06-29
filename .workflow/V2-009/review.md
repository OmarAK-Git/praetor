# Review — V2-009

## REVIEW-001 — Gate authorization layer

PolicyGate live never-contain checks now call `live_never_contain_blocks_containment_authorization` from `config/emergency.py` via `_live_never_contain_blocks_authorization`. Snapshot never-contain remains on `target_blocked_by_snapshot` (org-config permanent list).

## REVIEW-002 — Revocation ledger append policy

**Unified:** activation (`activate_org_config`), emergency (`add_emergency_never_contain`), and recovery (`reconcile_outstanding_directives_never_contain`) all revoke via `revoke_directives_matching_never_contain` → `automated_revoke_directive_in_transaction` → `append_ledger_record`. Evidence:

- `tests/config/test_config_activation.py::test_post_activation_reconciliation_writes_feed_outbox_and_keeps_idempotency`
- `tests/config/test_emergency_never_contain.py::test_emergency_persists_outbox_and_revokes_conflict`
- `tests/engine/test_crash_recovery.py::test_startup_scans_outstanding_directives_against_never_contain`

No code change required — gap was documentation/verification only.

## REVIEW-003 — Intake path coverage

Added `emergency_never_contain_intake.yaml` (engine_intake runner) and `test_intake_emergency_never_contain_blocks_at_authorization`. Harness `_run_engine_intake` now applies `_apply_emergency_never_contain_setup`.

## Gaps

- `docs/contracts.md` §13 fault-flag rows unchanged (task hard limit).
- Full-suite pytest in fresh worktree on Windows shows unrelated CRLF/splunk failures; main workspace baseline at V2-005+ uncommitted is 796 passed.
