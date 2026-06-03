"""Emergency never-contain entries (authenticated SOC-lead surface)."""

from __future__ import annotations

import uuid
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
    directive_matches_entry,
    emergency_entry_as_never_contain,
    target_in_never_contain_list,
)
from praetor.config.state import (
    fetch_active_snapshot,
    fetch_outstanding_unrevoked_directives,
    insert_emergency_record,
    mark_directive_revoked,
    read_live_never_contain_entries,
)
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.ledger import (
    DirectiveRevocationRecord,
    EmergencyNeverContainRecord,
    RevocationReason,
)
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
        entry_dict = emergency_entry_as_never_contain(record)
        for directive in fetch_outstanding_unrevoked_directives(store.conn):
            if not directive_matches_entry(directive, entry_dict):
                continue
            now = datetime.now(UTC)
            rev = DirectiveRevocationRecord(
                revocation_id=f"rev-{uuid.uuid4().hex}",
                directive_id=directive.directive_id,
                reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
                reason_code=RevocationReason.NEVER_CONTAIN_CONFLICT.value,
                triggered_by=added_by,
                revoked_at=now,
                ledger_commit_at=now,
                idempotency_key_cleared=False,
            )
            store.write_automated_revocation_in_transaction(rev)
            mark_directive_revoked(store.conn, directive.directive_id)
            revoked_ids.append(directive.directive_id)

        alerts: list[SystemHealthAlert] = [
            SystemHealthAlert(
                alert_code="emergency_never_contain_entry_created",
                emitted_at=datetime.now(UTC),
            )
        ]
        alerts.extend(
            SystemHealthAlert(
                alert_code="never_contain_conflict",
                emitted_at=datetime.now(UTC),
            )
            for _ in revoked_ids
        )
        enqueue_health_alerts_in_transaction(store.conn, alerts, batch_id=batch_id)

    emitted.extend(flush_health_alert_batch(store.conn, batch_id=batch_id))

    return EmergencyEntryResult(
        record=record,
        revoked_directive_ids=revoked_ids,
        emitted_alert_ids=emitted,
        health_alert_batch_id=batch_id,
    )


def emergency_cannot_authorize_containment(
    *,
    proposed_disposition: str,
    target_type: str,
    target_id: str,
    live_entries: list[dict[str, Any]],
) -> bool:
    if proposed_disposition != "auto_contain":
        return False
    return target_in_never_contain_list(target_type, target_id, live_entries)
