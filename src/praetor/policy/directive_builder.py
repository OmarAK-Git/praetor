"""Build ContainmentDirective records from PolicyGate authorization."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

from praetor.config.live import combined_live_never_contain_entries
from praetor.config.state import fetch_active_emergency_records
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.hashing import compute_never_contain_entries_hash, derive_idempotency_key
from praetor.policy.containment_policy import (
    ContainmentTarget,
    embedded_entries_for_target,
    snapshot_never_contain_entries,
)
from praetor.revocation.outbox import read_last_verified_exported_sequence


def build_containment_directive_in_transaction(
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
    moment = now or datetime.now(UTC)
    lifetime = org_snapshot.directive_lifetime_policy.max_lifetime_seconds
    expires_at = moment + timedelta(seconds=lifetime)
    permanent = snapshot_never_contain_entries(org_snapshot)
    emergencies = fetch_active_emergency_records(conn, now=moment)
    combined = combined_live_never_contain_entries(permanent, emergencies, now=moment)
    embedded = embedded_entries_for_target(combined, target)
    if not embedded:
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
        # §9: hash the embedded target-relevant subset, not the full live list.
        live_never_contain_hash=compute_never_contain_entries_hash(embedded_dicts),
        embedded_never_contain_entries=embedded_dicts,
        minimum_feed_sequence_at_issue=read_last_verified_exported_sequence(conn),
        supersedes_directive_id=supersedes_directive_id,
    )
