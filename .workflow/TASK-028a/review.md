# Review: TASK-028a (gatekeeper follow-up)

## Closed in follow-up

1. **Eval directive coverage:** `_run_engine_intake` now asserts `directive_emitted` / target fields via `outstanding_containment_directives`; `_validate_expectations` rejects unconsumed expectation keys per runner.
2. **Stamp-before-ledger ordering:** Intake calls `evaluate_policy_gate(..., persist_directive=False)`; directive durability + edict + snapshot commit in one `critical_transaction` after terminal stamp (DEC-049). In-flight stamp (`unknown`/`pending` backend) leaves no orphaned directive.
3. **Auto-contain + stamp failed:** Intake preserves `auto_contain` candidate + `ticket_stamp_failed` per spec Outcome Matrix; directive persisted with edict (`auto_contain_stamp_failed` scenario + engine tests).
4. **Metrics on incomplete actuation:** Policy-gate/disposition/containment metrics recorded only after terminal stamp + ledger append; unknown-stamp early return records nothing.
5. **Deferred persist conflict (in-band escalate):** `DeferredDirectivePersistConflict` caught inside edict-append transaction; directive suppressed, edict rebuilt as escalate with gate fault flag; attempt completes in-band (no uncaught `RuntimeError` / STAMP_RESOLVED orphan).
6. **Repo hygiene:** `tmp-*.db` in `.gitignore` for stray SQLite debug artifacts.

## Remaining gaps

1. **Feed export lag metrics:** `record_feed_export_lag` still not called from intake (no export completion event at intake time).
2. **Recovery path:** `engine/recovery.py` still hard-downgrades `auto_contain` on stamp recovery (intentional safety per DEC-009 review test); not re-run through PolicyGate.
3. **Fault-flag static guard (phase-2 T3):** not added.

## Doc alignment

Behavior matches `docs/spec.md` § Ticket Stamp Contract (`Stamping precedes ledger write`) and Outcome Matrix stamp-failure row (candidate preserved).
