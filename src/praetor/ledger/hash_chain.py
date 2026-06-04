"""Hash-chain link computation and integrity verification."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from praetor.contracts.edict import DecisionEdict
from praetor.contracts.ledger import (
    DirectiveRevocationRecord,
    EmergencyNeverContainRecord,
    NeverContainSnapshotRecord,
)
from praetor.hashing.canonical import CanonicalSerializationError
from praetor.hashing.domains import (
    compute_ledger_link_hash,
    compute_never_contain_entries_hash,
)

KNOWN_LEDGER_RECORD_TYPES = frozenset(
    {
        "decision_edict",
        "directive_revocation",
        "never_contain_snapshot",
        "emergency_never_contain",
    }
)

DECISION_EDICT_RECORD_TYPE = "decision_edict"
NEVER_CONTAIN_SNAPSHOT_RECORD_TYPE = "never_contain_snapshot"

LEDGER_RECORD_MODELS: dict[str, type[BaseModel]] = {
    DECISION_EDICT_RECORD_TYPE: DecisionEdict,
    "directive_revocation": DirectiveRevocationRecord,
    NEVER_CONTAIN_SNAPSHOT_RECORD_TYPE: NeverContainSnapshotRecord,
    "emergency_never_contain": EmergencyNeverContainRecord,
}

_TModel = TypeVar("_TModel", bound=BaseModel)


class LedgerChainIntegrityError(Exception):
    """Raised when stored ledger rows fail hash-chain verification."""


def record_body_for_chain_hash(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return the record payload hashed into the chain link (docs/contracts.md §7a)."""
    if "record_type" not in record:
        msg = "ledger record missing record_type"
        raise LedgerChainIntegrityError(msg)
    record_type = record["record_type"]
    if not isinstance(record_type, str):
        msg = "ledger record_type must be a string"
        raise LedgerChainIntegrityError(msg)
    validate_known_record_type(record_type)
    if record_type == DECISION_EDICT_RECORD_TYPE:
        return {
            key: value
            for key, value in record.items()
            if key not in ("ledger_previous_hash", "ledger_current_hash")
        }
    return dict(record)


def validate_ledger_record_contract(record: Mapping[str, Any]) -> BaseModel:
    """Validate a parsed ledger row against its full Pydantic contract (§7a)."""
    record_type = record.get("record_type")
    if record_type is None:
        msg = "ledger record missing record_type"
        raise LedgerChainIntegrityError(msg)
    if not isinstance(record_type, str):
        msg = "ledger record_type must be a string"
        raise LedgerChainIntegrityError(msg)
    validate_known_record_type(record_type)
    model_type = LEDGER_RECORD_MODELS[record_type]
    return _model_from_parsed_record(dict(record), model_type)


def validate_known_record_type(record_type: str) -> None:
    if record_type not in KNOWN_LEDGER_RECORD_TYPES:
        msg = f"unrecognized ledger record_type: {record_type!r}"
        raise LedgerChainIntegrityError(msg)


def validate_never_contain_snapshot_hash(snapshot: NeverContainSnapshotRecord) -> None:
    """Require snapshot_hash to match canonical hash of snapshot_content (§9 / §7a)."""
    expected = compute_never_contain_entries_hash(snapshot.snapshot_content)
    if snapshot.snapshot_hash != expected:
        msg = (
            "never_contain_snapshot snapshot_hash does not match "
            "canonical hash of snapshot_content"
        )
        raise LedgerChainIntegrityError(msg)


def verify_edict_never_contain_audit_link(
    edict: DecisionEdict,
    snapshot: NeverContainSnapshotRecord,
) -> None:
    """Verify DecisionEdict.live_never_contain_hash matches chained snapshot (§9)."""
    if snapshot.triggered_by_decision_id != edict.decision_id:
        msg = (
            f"never_contain_snapshot triggered_by_decision_id "
            f"{snapshot.triggered_by_decision_id!r} does not match edict "
            f"decision_id {edict.decision_id!r}"
        )
        raise LedgerChainIntegrityError(msg)
    validate_never_contain_snapshot_hash(snapshot)
    content_hash = compute_never_contain_entries_hash(snapshot.snapshot_content)
    if edict.live_never_contain_hash != content_hash:
        msg = (
            "decision edict live_never_contain_hash does not match "
            "never_contain_snapshot snapshot_content hash"
        )
        raise LedgerChainIntegrityError(msg)


def find_never_contain_snapshot_for_decision(
    conn: sqlite3.Connection,
    decision_id: str,
) -> NeverContainSnapshotRecord | None:
    """Return the first never_contain_snapshot row linked to decision_id, if any."""
    rows = conn.execute(
        """
        SELECT record_json FROM ledger_chain
        WHERE record_type = ?
        ORDER BY chain_sequence ASC
        """,
        (NEVER_CONTAIN_SNAPSHOT_RECORD_TYPE,),
    ).fetchall()
    for row in rows:
        record = _parse_ledger_record_json(str(row["record_json"]), sequence=-1)
        if str(record.get("record_type")) != NEVER_CONTAIN_SNAPSHOT_RECORD_TYPE:
            continue
        snapshot = _model_from_parsed_record(record, NeverContainSnapshotRecord)
        if snapshot.triggered_by_decision_id == decision_id:
            return snapshot
    return None


def verify_edict_has_matching_never_contain_snapshot(
    conn: sqlite3.Connection,
    edict: DecisionEdict,
) -> None:
    """Locate snapshot by triggered_by_decision_id and verify audit hash link."""
    snapshot = find_never_contain_snapshot_for_decision(conn, edict.decision_id)
    if snapshot is None:
        msg = (
            f"no never_contain_snapshot record for decision_id {edict.decision_id!r}"
        )
        raise LedgerChainIntegrityError(msg)
    verify_edict_never_contain_audit_link(edict, snapshot)


def _parse_ledger_record_json(record_json: str, *, sequence: int) -> dict[str, Any]:
    try:
        parsed = json.loads(record_json)
    except json.JSONDecodeError as exc:
        msg = f"malformed ledger record_json at sequence {sequence}"
        raise LedgerChainIntegrityError(msg) from exc
    if not isinstance(parsed, dict):
        msg = f"ledger record_json must be an object at sequence {sequence}"
        raise LedgerChainIntegrityError(msg)
    return parsed


def _model_from_parsed_record(
    record: dict[str, Any],
    model_type: type[_TModel],
) -> _TModel:
    try:
        return model_type.model_validate(record)
    except ValidationError as exc:
        msg = "ledger record failed contract validation"
        raise LedgerChainIntegrityError(msg) from exc


def _recompute_link_hash(
    *,
    previous_hash: str | None,
    record: Mapping[str, Any],
) -> str:
    try:
        body = record_body_for_chain_hash(record)
        return compute_ledger_link_hash(previous_hash=previous_hash, record=body)
    except CanonicalSerializationError as exc:
        msg = "ledger record body is not canonically serializable"
        raise LedgerChainIntegrityError(msg) from exc


def verify_record_chain_link(
    *,
    previous_hash: str | None,
    record: Mapping[str, Any],
    expected_current_hash: str,
) -> None:
    """Verify one chain link against its stored current hash."""
    record_type = record.get("record_type")
    if record_type is None:
        msg = "ledger record missing record_type"
        raise LedgerChainIntegrityError(msg)
    if not isinstance(record_type, str):
        msg = "ledger record_type must be a string"
        raise LedgerChainIntegrityError(msg)

    validate_known_record_type(record_type)
    validate_ledger_record_contract(record)

    if not expected_current_hash:
        msg = "ledger row missing ledger_current_hash"
        raise LedgerChainIntegrityError(msg)

    recomputed = _recompute_link_hash(previous_hash=previous_hash, record=record)
    if recomputed != expected_current_hash:
        msg = (
            f"ledger chain hash mismatch for record_type={record_type!r}: "
            f"expected {expected_current_hash!r}, got {recomputed!r}"
        )
        raise LedgerChainIntegrityError(msg)

    if record_type == DECISION_EDICT_RECORD_TYPE:
        stored_previous = record.get("ledger_previous_hash")
        if previous_hash is None:
            if stored_previous is not None:
                msg = "genesis edict must have ledger_previous_hash=null"
                raise LedgerChainIntegrityError(msg)
        elif stored_previous != previous_hash:
            msg = "decision edict ledger_previous_hash does not match chain tip"
            raise LedgerChainIntegrityError(msg)
        stored_current = record.get("ledger_current_hash")
        if stored_current != expected_current_hash:
            msg = "decision edict ledger_current_hash does not match chain row"
            raise LedgerChainIntegrityError(msg)


def verify_ledger_chain(conn: sqlite3.Connection) -> None:
    """Walk the ledger table and verify every link."""
    try:
        rows = conn.execute(
            """
            SELECT chain_sequence, record_type, record_json,
                   ledger_previous_hash, ledger_current_hash
            FROM ledger_chain
            ORDER BY chain_sequence ASC
            """
        ).fetchall()
    except sqlite3.Error as exc:
        msg = "failed to read ledger_chain table"
        raise LedgerChainIntegrityError(msg) from exc

    previous_hash: str | None = None
    for row in rows:
        sequence = int(row["chain_sequence"])
        record_type = row["record_type"]
        if record_type is None:
            msg = f"ledger row missing record_type at sequence {sequence}"
            raise LedgerChainIntegrityError(msg)
        record_type = str(record_type)

        validate_known_record_type(record_type)
        record = _parse_ledger_record_json(str(row["record_json"]), sequence=sequence)

        json_type = record.get("record_type")
        if json_type is None:
            msg = f"ledger record_json missing record_type at sequence {sequence}"
            raise LedgerChainIntegrityError(msg)
        if str(json_type) != record_type:
            msg = (
                f"record_type mismatch at sequence {sequence}: "
                f"column={record_type!r}, json={json_type!r}"
            )
            raise LedgerChainIntegrityError(msg)

        stored_previous = row["ledger_previous_hash"]
        if previous_hash is None:
            if stored_previous is not None:
                msg = "genesis row must have ledger_previous_hash=null"
                raise LedgerChainIntegrityError(msg)
        elif stored_previous != previous_hash:
            msg = (
                f"broken chain at sequence {sequence}: "
                "ledger_previous_hash does not match prior tip"
            )
            raise LedgerChainIntegrityError(msg)

        current_cell = row["ledger_current_hash"]
        if current_cell is None:
            msg = f"ledger row missing ledger_current_hash at sequence {sequence}"
            raise LedgerChainIntegrityError(msg)
        expected_current = str(current_cell)

        verify_record_chain_link(
            previous_hash=previous_hash,
            record=record,
            expected_current_hash=expected_current,
        )
        previous_hash = expected_current
