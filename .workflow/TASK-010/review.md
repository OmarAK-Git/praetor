# Review: TASK-010 (revised)

## Resolved gaps

| Gap (prior pass) | Resolution |
|------------------|------------|
| Ledger link formula not in contracts | **§7a added** to `docs/contracts.md` with domain, genesis token, body rules, test vector, deletion boundaries |
| Startup hook not wired | `run_ledger_startup_hook` called from `open_state_store` after schema init |
| Schema nullable drift | `decision_edict.json` export + drift/nullable tests |
| Error taxonomy | All verification failures normalized to `LedgerChainIntegrityError` |

## Intentional deferrals (Task 11–12)

- Revocation/emergency/config write paths do not call `append_ledger_record`
- Full startup orchestrator (attempt recovery, feed export) not built
- PolicyGate / intake not wired

## Chain verification boundaries (§7a)

- **Middle deletion:** detected (`test_middle_deletion_breaks_chain`)
- **Tail truncation:** not detectable without external tip (`test_tail_truncation_may_verify`)

## Findings

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| R-001 | fixed | contracts §7a pin | closed |
| R-002 | fixed | startup hook in `open_state_store` | closed |
| R-003 | note | `NeverContainSnapshotRecord` validator breaks fixtures using wrong hash | fixed in conftest |
