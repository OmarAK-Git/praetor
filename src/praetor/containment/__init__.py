"""Containment directive lifecycle and revocation (Task 20)."""

from praetor.containment.lifecycle import (
    build_proposed_directive_in_transaction,
    commit_outstanding_directive,
    emit_directive,
    insert_outstanding_directive_in_transaction,
    verify_consumer_embedded_hash,
)
from praetor.containment.revocation import (
    NEVER_CONTAIN_CONFLICT_ALERT,
    POST_ACTIVATION_CONFLICT_ALERT,
    automated_revoke_directive_in_transaction,
    manual_revoke_directive,
    new_revocation_record,
    revoke_directives_matching_never_contain,
    revoke_supersession_in_transaction,
)

__all__ = [
    "NEVER_CONTAIN_CONFLICT_ALERT",
    "POST_ACTIVATION_CONFLICT_ALERT",
    "automated_revoke_directive_in_transaction",
    "build_proposed_directive_in_transaction",
    "commit_outstanding_directive",
    "emit_directive",
    "insert_outstanding_directive_in_transaction",
    "manual_revoke_directive",
    "new_revocation_record",
    "revoke_directives_matching_never_contain",
    "revoke_supersession_in_transaction",
    "verify_consumer_embedded_hash",
]
