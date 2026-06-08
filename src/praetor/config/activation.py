"""Org config activation with preflight and post-activation reconciliation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from praetor.auth.verifier import (
    TokenVerifier,
    authenticate_org_config_activation,
    verified_record_identity,
)
from praetor.config.errors import ActivationError, PreflightError
from praetor.config.health_emit import (
    drain_unflushed_health_alerts,
    enqueue_health_alerts_in_transaction,
    flush_health_alert_batch,
    new_health_alert_batch_id,
)
from praetor.config.live import directive_matches_entry, permanent_never_contain_entries
from praetor.config.loader import load_org_config_source
from praetor.config.preflight import run_preflight
from praetor.config.state import (
    activate_org_config_record,
    fetch_active_emergency_records,
    fetch_outstanding_unrevoked_directives,
    mark_directive_revoked,
    retire_emergencies_absorbed_into_permanent,
)
from praetor.contracts.containment import ContainmentDirective
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason
from praetor.ledger.store import append_ledger_record
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import StateStore


@dataclass
class ActivationResult:
    snapshot_hash: str
    revoked_directive_ids: list[str] = field(default_factory=list)
    retired_emergency_entry_ids: list[str] = field(default_factory=list)
    emitted_alert_ids: list[str] = field(default_factory=list)
    health_alert_batch_id: str = ""


def _revocation_for_directive(
    directive: ContainmentDirective,
    *,
    reason: RevocationReason,
    triggered_by: str,
) -> DirectiveRevocationRecord:
    now = datetime.now(UTC)
    return DirectiveRevocationRecord(
        revocation_id=f"rev-{uuid.uuid4().hex}",
        directive_id=directive.directive_id,
        reason=reason,
        reason_code=reason.value,
        triggered_by=triggered_by,
        revoked_at=now,
        ledger_commit_at=now,
        idempotency_key_cleared=False,
    )


def activate_org_config(
    store: StateStore,
    config_path: Path,
    *,
    token: str | None,
    verifier: TokenVerifier,
) -> ActivationResult:
    principal = authenticate_org_config_activation(token, verifier)
    triggered_by = verified_record_identity(principal)

    loaded = load_org_config_source(config_path)
    try:
        snapshot = run_preflight(loaded.document, verbatim_text=loaded.verbatim_text)
    except PreflightError as exc:
        raise ActivationError(exc) from exc

    permanent = permanent_never_contain_entries(
        snapshot.containment_exclusions.model_dump(mode="json")
    )
    batch_id = new_health_alert_batch_id()
    revoked_ids: list[str] = []
    retired_emergency: list[str] = []
    emitted: list[str] = drain_unflushed_health_alerts(store.conn)

    with critical_transaction(store.conn):
        emergencies = fetch_active_emergency_records(store.conn)
        from praetor.config.live import reconciliation_never_contain_entries

        never_contain = reconciliation_never_contain_entries(permanent, emergencies)
        directives = fetch_outstanding_unrevoked_directives(store.conn)
        for directive in directives:
            if not any(directive_matches_entry(directive, e) for e in never_contain):
                continue
            record = _revocation_for_directive(
                directive,
                reason=RevocationReason.POST_ACTIVATION_RECONCILIATION,
                triggered_by=triggered_by,
            )
            store.write_automated_revocation_in_transaction(record)
            append_ledger_record(store.conn, record)
            mark_directive_revoked(store.conn, directive.directive_id)
            revoked_ids.append(directive.directive_id)

        retired_emergency = retire_emergencies_absorbed_into_permanent(
            store.conn, permanent
        )
        activate_org_config_record(
            store.conn,
            snapshot,
            verbatim_render_text=loaded.verbatim_text,
        )
        alerts = [
            SystemHealthAlert(
                alert_code="never_contain_post_activation_conflict",
                emitted_at=datetime.now(UTC),
            )
            for _ in revoked_ids
        ]
        enqueue_health_alerts_in_transaction(store.conn, alerts, batch_id=batch_id)

    emitted.extend(flush_health_alert_batch(store.conn, batch_id=batch_id))

    return ActivationResult(
        snapshot_hash=snapshot.snapshot_hash,
        revoked_directive_ids=revoked_ids,
        retired_emergency_entry_ids=retired_emergency,
        emitted_alert_ids=emitted,
        health_alert_batch_id=batch_id,
    )
