"""Differentiated directive revocation triggers with ledger + feed projection."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

from praetor.config.live import directive_matches_entry
from praetor.config.state import mark_directive_revoked
from praetor.contracts.containment import ContainmentDirective
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason
from praetor.ledger.store import append_ledger_record
from praetor.state.sqlite_guard import (
    critical_transaction,
    require_critical_transaction,
)
from praetor.state.store import RevocationWriteResult, StateStore

NEVER_CONTAIN_CONFLICT_ALERT = "never_contain_conflict"
POST_ACTIVATION_CONFLICT_ALERT = "never_contain_post_activation_conflict"
ORPHAN_OUTSTANDING_DIRECTIVE_ALERT = "orphan_outstanding_directive"


def new_revocation_record(
    directive: ContainmentDirective,
    *,
    reason: RevocationReason,
    triggered_by: str,
    idempotency_key_cleared: bool,
    superseded_by_directive_id: str | None = None,
    now: datetime | None = None,
) -> DirectiveRevocationRecord:
    moment = now or datetime.now(UTC)
    return DirectiveRevocationRecord(
        revocation_id=f"rev-{uuid.uuid4().hex}",
        directive_id=directive.directive_id,
        reason=reason,
        reason_code=reason.value,
        triggered_by=triggered_by,
        revoked_at=moment,
        ledger_commit_at=moment,
        idempotency_key_cleared=idempotency_key_cleared,
        superseded_by_directive_id=superseded_by_directive_id,
    )


def automated_revoke_directive_in_transaction(
    conn: sqlite3.Connection,
    store: StateStore,
    directive: ContainmentDirective,
    record: DirectiveRevocationRecord,
) -> RevocationWriteResult:
    """Write automated revocation record, feed row, and ledger append in one tx."""
    require_critical_transaction(conn)
    result = store.write_automated_revocation_in_transaction(record)
    append_ledger_record(conn, record)
    mark_directive_revoked(conn, directive.directive_id)
    return result


def revoke_supersession_in_transaction(
    conn: sqlite3.Connection,
    store: StateStore,
    directive: ContainmentDirective,
    *,
    superseded_by_directive_id: str,
    triggered_by: str,
    now: datetime | None = None,
) -> RevocationWriteResult:
    record = new_revocation_record(
        directive,
        reason=RevocationReason.SUPERSESSION,
        triggered_by=triggered_by,
        idempotency_key_cleared=False,
        superseded_by_directive_id=superseded_by_directive_id,
        now=now,
    )
    return automated_revoke_directive_in_transaction(conn, store, directive, record)


def manual_revoke_directive_in_transaction(
    conn: sqlite3.Connection,
    store: StateStore,
    directive: ContainmentDirective,
    record: DirectiveRevocationRecord,
    *,
    idempotency_key: str,
) -> RevocationWriteResult:
    """Manual revocation: ledger append, feed row, key clear in one transaction."""
    require_critical_transaction(conn)
    result = store.write_manual_revocation_in_transaction(
        record,
        idempotency_key=idempotency_key,
    )
    append_ledger_record(conn, record)
    mark_directive_revoked(conn, directive.directive_id)
    return result


def manual_revoke_directive(
    store: StateStore,
    directive: ContainmentDirective,
    *,
    idempotency_key: str,
    triggered_by: str,
    now: datetime | None = None,
) -> RevocationWriteResult:
    """SOC-lead manual revocation in one transaction (ledger, feed, key clear)."""
    record = new_revocation_record(
        directive,
        reason=RevocationReason.MANUAL,
        triggered_by=triggered_by,
        idempotency_key_cleared=True,
        now=now,
    )
    with critical_transaction(store.conn):
        return manual_revoke_directive_in_transaction(
            store.conn,
            store,
            directive,
            record,
            idempotency_key=idempotency_key,
        )


def revoke_directives_matching_never_contain(
    conn: sqlite3.Connection,
    store: StateStore,
    directives: list[ContainmentDirective],
    never_contain_entries: list[dict[str, object]],
    *,
    reason: RevocationReason,
    triggered_by: str,
    now: datetime | None = None,
) -> list[str]:
    """Revoke directives whose targets match never-contain entries; key not cleared."""
    require_critical_transaction(conn)
    revoked_ids: list[str] = []
    moment = now or datetime.now(UTC)
    for directive in directives:
        matches = (
            directive_matches_entry(directive, e) for e in never_contain_entries
        )
        if not any(matches):
            continue
        record = new_revocation_record(
            directive,
            reason=reason,
            triggered_by=triggered_by,
            idempotency_key_cleared=False,
            now=moment,
        )
        automated_revoke_directive_in_transaction(conn, store, directive, record)
        revoked_ids.append(directive.directive_id)
    return revoked_ids


def never_contain_conflict_alerts(
    count: int, *, now: datetime | None = None
) -> list[SystemHealthAlert]:
    moment = now or datetime.now(UTC)
    return [
        SystemHealthAlert(alert_code=NEVER_CONTAIN_CONFLICT_ALERT, emitted_at=moment)
        for _ in range(count)
    ]


def post_activation_conflict_alerts(
    count: int, *, now: datetime | None = None
) -> list[SystemHealthAlert]:
    moment = now or datetime.now(UTC)
    return [
        SystemHealthAlert(
            alert_code=POST_ACTIVATION_CONFLICT_ALERT,
            emitted_at=moment,
        )
        for _ in range(count)
    ]


def orphan_outstanding_directive_alert(
    *, now: datetime | None = None
) -> SystemHealthAlert:
    moment = now or datetime.now(UTC)
    return SystemHealthAlert(
        alert_code=ORPHAN_OUTSTANDING_DIRECTIVE_ALERT,
        emitted_at=moment,
    )
