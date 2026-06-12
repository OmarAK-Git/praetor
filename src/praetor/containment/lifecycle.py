"""ContainmentDirective lifecycle: build, emit, persist, consumer hash verify."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.hashing import compute_never_contain_entries_hash, derive_idempotency_key
from praetor.revocation.outbox import read_last_verified_exported_sequence
from praetor.state.sqlite_guard import (
    critical_transaction,
    require_critical_transaction,
)

if TYPE_CHECKING:
    from praetor.policy.containment_policy import ContainmentTarget


def build_proposed_directive_in_transaction(
    conn: sqlite3.Connection,
    *,
    decision_id: str,
    alert_identity: str,
    target: ContainmentTarget,
    evidence_refs: list[str],
    org_snapshot: OrgConfigSnapshot,
    live_never_contain_entries: list[dict[str, object]],
    now: datetime | None = None,
    supersedes_directive_id: str | None = None,
) -> ContainmentDirective:
    """Build a proposed directive with embedded never-contain subset and feed floor."""
    from praetor.policy.containment_policy import embedded_entries_for_target

    require_critical_transaction(conn)
    moment = now or datetime.now(UTC)
    lifetime = org_snapshot.directive_lifetime_policy.max_lifetime_seconds
    expires_at = moment + timedelta(seconds=lifetime)
    embedded = embedded_entries_for_target(live_never_contain_entries, target)
    embedded_dicts = [dict(e) for e in embedded]
    idempotency_key = derive_idempotency_key(
        alert_identity,
        target.target_type,
        target.target_id,
        target.scope,
    )
    return ContainmentDirective(
        directive_id=f"dir-{uuid.uuid4().hex}",
        decision_id=decision_id,
        target_type=TargetType(target.target_type),
        target_id=target.target_id,
        scope=target.scope,
        evidence_refs=evidence_refs,
        issued_at=moment,
        expires_at=expires_at,
        idempotency_key=idempotency_key,
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.PROPOSED,
        live_never_contain_hash=compute_never_contain_entries_hash(embedded_dicts),
        embedded_never_contain_entries=embedded_dicts,
        minimum_feed_sequence_at_issue=read_last_verified_exported_sequence(conn),
        supersedes_directive_id=supersedes_directive_id,
    )


def emit_directive(directive: ContainmentDirective) -> ContainmentDirective:
    """Transition a proposed directive to emitted status."""
    if directive.status == DirectiveStatus.EMITTED:
        return directive
    if directive.status != DirectiveStatus.PROPOSED:
        msg = f"cannot emit directive in status {directive.status.value!r}"
        raise ValueError(msg)
    return directive.model_copy(update={"status": DirectiveStatus.EMITTED})


def verify_consumer_embedded_hash(directive: ContainmentDirective) -> bool:
    """Consumer-side transit integrity check for embedded never-contain entries (§9)."""
    recomputed = compute_never_contain_entries_hash(
        directive.embedded_never_contain_entries
    )
    return recomputed == directive.live_never_contain_hash


def insert_outstanding_directive_in_transaction(
    conn: sqlite3.Connection,
    directive: ContainmentDirective,
) -> ContainmentDirective:
    """Persist a committed directive as emitted.

    Caller must hold ``critical_transaction``.
    """
    require_critical_transaction(conn)
    emitted = emit_directive(directive)
    conn.execute(
        """
        INSERT INTO outstanding_containment_directives (
            directive_id, directive_json, issued_at, expires_at,
            target_type, target_id, revoked
        ) VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (
            emitted.directive_id,
            emitted.model_dump_json(),
            emitted.issued_at.isoformat(),
            emitted.expires_at.isoformat(),
            emitted.target_type.value,
            emitted.target_id,
        ),
    )
    return emitted


def commit_outstanding_directive(
    conn: sqlite3.Connection,
    directive: ContainmentDirective,
) -> ContainmentDirective:
    """Record a committed directive for reconciliation scans (internal/tests)."""
    with critical_transaction(conn):
        return insert_outstanding_directive_in_transaction(conn, directive)
