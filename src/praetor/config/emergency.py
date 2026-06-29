"""Emergency never-contain entries (authenticated SOC-lead surface)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from praetor.auth.verifier import (
    TokenVerifier,
    authenticate_emergency_never_contain,
    verified_record_identity,
)
from praetor.config.errors import PreflightError
from praetor.config.health_emit import (
    drain_unflushed_health_alerts,
    enqueue_health_alerts_in_transaction,
    flush_health_alert_batch,
    new_health_alert_batch_id,
)
from praetor.config.live import (
    canonical_target_specification,
    emergency_entry_as_never_contain,
    target_in_never_contain_list,
)
from praetor.config.state import (
    fetch_active_snapshot,
    fetch_outstanding_unrevoked_directives,
    insert_emergency_record,
    read_live_never_contain_entries,
)
from praetor.containment.revocation import (
    never_contain_conflict_alerts,
    revoke_directives_matching_never_contain,
)
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.ledger import EmergencyNeverContainRecord, RevocationReason
from praetor.ledger.store import append_ledger_record
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import StateStore

EMERGENCY_HARD_MAX_SECONDS = 48 * 3600


@dataclass
class EmergencyEntryResult:
    record: EmergencyNeverContainRecord
    revoked_directive_ids: list[str] = field(default_factory=list)
    emitted_alert_ids: list[str] = field(default_factory=list)
    health_alert_batch_id: str = ""


class EmergencyNeverContainError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _require_emergency_lifetime_seconds(value: Any) -> int:
    if type(value) is not int:
        raise EmergencyNeverContainError(
            "invalid_emergency_lifetime",
            "lifetime_seconds must be an integer",
        )
    return value


def evaluate_live_never_contain_for_target(
    store: StateStore,
    *,
    target_type: str,
    target_id: str,
) -> bool:
    with critical_transaction(store.conn):
        entries = read_live_never_contain_entries(store.conn)
    return target_in_never_contain_list(target_type, target_id, entries)


def add_emergency_never_contain(
    store: StateStore,
    *,
    token: str | None,
    verifier: TokenVerifier,
    target_specification: dict[str, Any],
    lifetime_seconds: int,
    audit_reason: str,
    entry_id: str | None = None,
    _test_before_conflict_revocation: Callable[[], None] | None = None,
) -> EmergencyEntryResult:
    principal = authenticate_emergency_never_contain(token, verifier)
    added_by = verified_record_identity(principal)

    try:
        canonical_spec = canonical_target_specification(target_specification)
    except PreflightError as exc:
        raise EmergencyNeverContainError(exc.code, str(exc)) from exc

    lifetime_seconds = _require_emergency_lifetime_seconds(lifetime_seconds)
    if lifetime_seconds <= 0 or lifetime_seconds > EMERGENCY_HARD_MAX_SECONDS:
        raise EmergencyNeverContainError(
            "invalid_emergency_lifetime",
            "lifetime must be positive and at most 48 hours",
        )

    batch_id = new_health_alert_batch_id()
    revoked_ids: list[str] = []
    record: EmergencyNeverContainRecord
    emitted: list[str] = drain_unflushed_health_alerts(store.conn)

    with critical_transaction(store.conn):
        active = fetch_active_snapshot(store.conn)
        if active is None:
            raise EmergencyNeverContainError(
                "no_active_org_config",
                "emergency never-contain requires an activated org config",
            )
        policy_max = active.emergency_never_contain_policy.max_lifetime_seconds
        if lifetime_seconds > policy_max:
            raise EmergencyNeverContainError(
                "invalid_emergency_lifetime",
                "lifetime exceeds org emergency_never_contain_policy maximum",
            )

        now = datetime.now(UTC)
        record = EmergencyNeverContainRecord(
            entry_id=entry_id or f"enc-{uuid.uuid4().hex}",
            target_specification=canonical_spec,
            added_by=added_by,
            added_at=now,
            expires_at=now + timedelta(seconds=lifetime_seconds),
            audit_reason=audit_reason,
        )
        insert_emergency_record(store.conn, record)
        append_ledger_record(store.conn, record)
        entry_dict = emergency_entry_as_never_contain(record)
        if _test_before_conflict_revocation is not None:
            _test_before_conflict_revocation()
        directives = fetch_outstanding_unrevoked_directives(store.conn)
        revoked_ids = revoke_directives_matching_never_contain(
            store.conn,
            store,
            directives,
            [entry_dict],
            reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
            triggered_by=added_by,
            now=now,
        )

        alerts: list[SystemHealthAlert] = [
            SystemHealthAlert(
                alert_code="emergency_never_contain_entry_created",
                emitted_at=datetime.now(UTC),
            )
        ]
        alerts.extend(never_contain_conflict_alerts(len(revoked_ids), now=now))
        # Keep alert enqueue atomic with the emergency record, ledger appends, and feed rows.
        enqueue_health_alerts_in_transaction(store.conn, alerts, batch_id=batch_id)

    emitted.extend(flush_health_alert_batch(store.conn, batch_id=batch_id))

    return EmergencyEntryResult(
        record=record,
        revoked_directive_ids=revoked_ids,
        emitted_alert_ids=emitted,
        health_alert_batch_id=batch_id,
    )


def live_never_contain_blocks_containment_authorization(
    *,
    target_type: str,
    target_id: str,
    live_entries: list[dict[str, Any]],
) -> bool:
    """True when live emergency or permanent never-contain entries block authorization."""
    return target_in_never_contain_list(target_type, target_id, live_entries)


def emergency_cannot_authorize_containment(
    *,
    proposed_disposition: str,
    target_type: str,
    target_id: str,
    live_entries: list[dict[str, Any]],
) -> bool:
    if proposed_disposition != "auto_contain":
        return False
    return live_never_contain_blocks_containment_authorization(
        target_type=target_type,
        target_id=target_id,
        live_entries=live_entries,
    )
