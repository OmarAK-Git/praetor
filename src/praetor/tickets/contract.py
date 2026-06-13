"""Ticket stamp contract — disposition sequencing per Outcome Matrix."""

from __future__ import annotations

from dataclasses import dataclass

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.tickets.outbox import StampStatus

TICKET_STAMP_FAILED = "ticket_stamp_failed"


@dataclass(frozen=True)
class StampContractDisposition:
    """Pre/post-stamp disposition row; mirrors engine SkeletonDisposition fields."""

    final_disposition: Disposition
    fault_flags: list[str]
    system_fault_escalation: bool
    proposed_disposition: Disposition


def stamp_status_allows_edict_append(status: StampStatus) -> bool:
    """Only succeeded/failed permit ledger append; pending/unknown are in-flight."""
    return status in (StampStatus.SUCCEEDED, StampStatus.FAILED)


def candidate_judgment_from_stamp_payload(
    ticket_stamp_payload: dict[str, object],
) -> ModelJudgment | None:
    """Recover the candidate judgment stored in the stamp outbox payload."""
    raw = ticket_stamp_payload.get("candidate_judgment")
    if isinstance(raw, dict):
        return ModelJudgment.model_validate(raw)
    return None


def apply_terminal_stamp_to_disposition(
    stamp_status: StampStatus,
    *,
    pre_stamp_disposition: StampContractDisposition,
) -> StampContractDisposition:
    """Map a terminal stamp outcome onto the pre-stamp candidate disposition.

    Success preserves the candidate. Failure preserves the full candidate row
    (``final_disposition``, existing fault flags, ``system_fault_escalation``) and
    appends ``ticket_stamp_failed``. Callers must already apply policy overrides
    (e.g. ``auto_contain`` -> ``escalate``) before invoking this function.
    """
    if stamp_status == StampStatus.SUCCEEDED:
        return pre_stamp_disposition
    if stamp_status != StampStatus.FAILED:
        msg = f"stamp status {stamp_status.value!r} is not terminal for edict append"
        raise ValueError(msg)

    fault_flags = list(pre_stamp_disposition.fault_flags)
    if TICKET_STAMP_FAILED not in fault_flags:
        fault_flags.append(TICKET_STAMP_FAILED)
    return StampContractDisposition(
        final_disposition=pre_stamp_disposition.final_disposition,
        fault_flags=fault_flags,
        system_fault_escalation=pre_stamp_disposition.system_fault_escalation,
        proposed_disposition=pre_stamp_disposition.proposed_disposition,
    )
