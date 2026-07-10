"""Hash-chained append-only audit ledger (internal-only)."""

from praetor.ledger.hash_chain import (
    KNOWN_LEDGER_RECORD_TYPES,
    LedgerChainIntegrityError,
    find_never_contain_snapshot_for_decision,
    validate_ledger_record_contract,
    validate_never_contain_snapshot_hash,
    verify_edict_has_matching_never_contain_snapshot,
    verify_edict_never_contain_audit_link,
    verify_ledger_chain,
)
from praetor.ledger.startup import (
    LEDGER_CHAIN_INTEGRITY_ALERT_CODE,
    LedgerStartupError,
    run_ledger_startup_hook,
    verify_ledger_chain_at_startup,
)
from praetor.ledger.store import (
    LedgerAppendResult,
    LedgerChainRow,
    append_ledger_record,
    fetch_ledger_rows,
    fetch_ledger_tip_hash,
    init_ledger_schema,
)
from praetor.ledger.tip_anchor import (
    LedgerTipAnchorMismatchError,
    verify_ledger_tip_against_anchor,
)

__all__ = [
    "KNOWN_LEDGER_RECORD_TYPES",
    "LEDGER_CHAIN_INTEGRITY_ALERT_CODE",
    "LedgerAppendResult",
    "LedgerChainIntegrityError",
    "LedgerChainRow",
    "LedgerStartupError",
    "LedgerTipAnchorMismatchError",
    "append_ledger_record",
    "fetch_ledger_rows",
    "fetch_ledger_tip_hash",
    "find_never_contain_snapshot_for_decision",
    "init_ledger_schema",
    "run_ledger_startup_hook",
    "validate_ledger_record_contract",
    "validate_never_contain_snapshot_hash",
    "verify_edict_has_matching_never_contain_snapshot",
    "verify_edict_never_contain_audit_link",
    "verify_ledger_chain",
    "verify_ledger_chain_at_startup",
    "verify_ledger_tip_against_anchor",
]
