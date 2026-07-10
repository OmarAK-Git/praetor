"""Org config activation with preflight and post-activation reconciliation."""

from __future__ import annotations

import copy
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from praetor.auth.verifier import (
    TokenVerifier,
    authenticate_org_config_activation,
    verified_record_identity,
)
from praetor.codification.statute_curation import (
    StatuteCurationActivationAudit,
    StatuteCurationWorkflow,
    activation_ready_config,
    render_proposed_statute_yaml,
    with_activation_audit,
)
from praetor.config.errors import ActivationError, PreflightError
from praetor.config.health_emit import (
    drain_unflushed_health_alerts,
    enqueue_health_alerts_in_transaction,
    flush_health_alert_batch,
    new_health_alert_batch_id,
)
from praetor.config.live import permanent_never_contain_entries
from praetor.config.loader import load_org_config_source
from praetor.config.preflight import run_preflight
from praetor.config.state import (
    activate_org_config_record,
    fetch_active_emergency_records,
    fetch_outstanding_unrevoked_directives,
    retire_emergencies_absorbed_into_permanent,
)
from praetor.containment.revocation import (
    post_activation_conflict_alerts,
    revoke_directives_matching_never_contain,
)
from praetor.contracts.ledger import RevocationReason
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import StateStore


@dataclass
class ActivationResult:
    snapshot_hash: str
    revoked_directive_ids: list[str] = field(default_factory=list)
    retired_emergency_entry_ids: list[str] = field(default_factory=list)
    emitted_alert_ids: list[str] = field(default_factory=list)
    health_alert_batch_id: str = ""


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
        revoked_ids = revoke_directives_matching_never_contain(
            store.conn,
            store,
            directives,
            never_contain,
            reason=RevocationReason.POST_ACTIVATION_RECONCILIATION,
            triggered_by=triggered_by,
        )

        retired_emergency = retire_emergencies_absorbed_into_permanent(
            store.conn, permanent
        )
        activate_org_config_record(
            store.conn,
            snapshot,
            verbatim_render_text=loaded.verbatim_text,
        )
        enqueue_health_alerts_in_transaction(
            store.conn,
            post_activation_conflict_alerts(len(revoked_ids)),
            batch_id=batch_id,
        )

    emitted.extend(flush_health_alert_batch(store.conn, batch_id=batch_id))

    return ActivationResult(
        snapshot_hash=snapshot.snapshot_hash,
        revoked_directive_ids=revoked_ids,
        retired_emergency_entry_ids=retired_emergency,
        emitted_alert_ids=emitted,
        health_alert_batch_id=batch_id,
    )


def promote_statute_curation(
    store: StateStore,
    workflow: StatuteCurationWorkflow,
    *,
    token: str | None,
    verifier: TokenVerifier,
    output_path: Path | None = None,
    activation_ready: bool = True,
) -> tuple[StatuteCurationWorkflow, ActivationResult]:
    """SOC-lead promotion: full preflight activation with workflow audit trail."""
    principal = authenticate_org_config_activation(token, verifier)
    reviewer = verified_record_identity(principal)
    if workflow.reviewer is not None and workflow.reviewer != reviewer:
        msg = (
            "workflow reviewer does not match authenticated SOC lead "
            f"({workflow.reviewer!r} != {reviewer!r})"
        )
        raise ActivationError(PreflightError("reviewer_mismatch", msg))

    config_document = (
        activation_ready_config(workflow.proposed_config)
        if activation_ready
        else copy.deepcopy(workflow.proposed_config)
    )
    yaml_text = render_proposed_statute_yaml(config_document)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml_text, encoding="utf-8")
        config_path = output_path
        cleanup_path = False
    else:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        ) as handle:
            handle.write(yaml_text)
            config_path = Path(handle.name)
        cleanup_path = True

    try:
        activation = activate_org_config(
            store,
            config_path,
            token=token,
            verifier=verifier,
        )
    finally:
        if cleanup_path:
            config_path.unlink(missing_ok=True)

    audit = StatuteCurationActivationAudit(
        workflow_id=workflow.workflow_id,
        reviewer=reviewer,
        snapshot_hash=activation.snapshot_hash,
        activated_at=datetime.now(UTC),
        revoked_directive_ids=tuple(activation.revoked_directive_ids),
        retired_emergency_entry_ids=tuple(activation.retired_emergency_entry_ids),
        emitted_alert_ids=tuple(activation.emitted_alert_ids),
        health_alert_batch_id=activation.health_alert_batch_id,
    )
    updated = with_activation_audit(workflow, audit)
    return updated, activation
