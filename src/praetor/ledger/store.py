"""SQLite persistence for the hash-chained ledger."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from praetor.contracts.edict import DecisionEdict
from praetor.contracts.ledger import (
    DirectiveRevocationRecord,
    EmergencyNeverContainRecord,
    NeverContainSnapshotRecord,
)
from praetor.hashing.canonical import canonical_serialize
from praetor.hashing.domains import compute_ledger_link_hash
from praetor.ledger.hash_chain import (
    LedgerChainIntegrityError,
    record_body_for_chain_hash,
    validate_known_record_type,
    validate_ledger_record_contract,
)
from praetor.state.sqlite_guard import require_critical_transaction

_ALLOWED_LEDGER_APPEND_TYPES = (
    DecisionEdict,
    DirectiveRevocationRecord,
    NeverContainSnapshotRecord,
    EmergencyNeverContainRecord,
)

LedgerRecord = (
    DecisionEdict
    | DirectiveRevocationRecord
    | NeverContainSnapshotRecord
    | EmergencyNeverContainRecord
)

_LEDGER_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ledger_chain (
    chain_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT NOT NULL,
    record_json TEXT NOT NULL,
    ledger_previous_hash TEXT,
    ledger_current_hash TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class LedgerChainRow:
    chain_sequence: int
    record_type: str
    record_json: str
    ledger_previous_hash: str | None
    ledger_current_hash: str


@dataclass(frozen=True)
class LedgerAppendResult:
    chain_sequence: int
    record_type: str
    ledger_previous_hash: str | None
    ledger_current_hash: str
    record_json: str


def init_ledger_schema(conn: sqlite3.Connection) -> None:
    """Create ledger chain table if missing (additive upgrade)."""
    conn.executescript(_LEDGER_SCHEMA_SQL)


def fetch_ledger_tip_hash(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        """
        SELECT ledger_current_hash
        FROM ledger_chain
        ORDER BY chain_sequence DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    return str(row["ledger_current_hash"])


def fetch_ledger_rows(conn: sqlite3.Connection) -> list[LedgerChainRow]:
    rows = conn.execute(
        """
        SELECT chain_sequence, record_type, record_json,
               ledger_previous_hash, ledger_current_hash
        FROM ledger_chain
        ORDER BY chain_sequence ASC
        """
    ).fetchall()
    return [
        LedgerChainRow(
            chain_sequence=int(row["chain_sequence"]),
            record_type=str(row["record_type"]),
            record_json=str(row["record_json"]),
            ledger_previous_hash=(
                None
                if row["ledger_previous_hash"] is None
                else str(row["ledger_previous_hash"])
            ),
            ledger_current_hash=str(row["ledger_current_hash"]),
        )
        for row in rows
    ]


def _record_to_mapping(record: LedgerRecord) -> dict[str, Any]:
    if isinstance(record, BaseModel):
        return record.model_dump(mode="python")
    msg = f"unsupported ledger record type: {type(record)!r}"
    raise TypeError(msg)


def append_ledger_record(
    conn: sqlite3.Connection,
    record: LedgerRecord,
) -> LedgerAppendResult:
    """Append one interleaved ledger record inside an open critical transaction."""
    require_critical_transaction(conn)

    if not isinstance(record, _ALLOWED_LEDGER_APPEND_TYPES):
        msg = f"unsupported ledger record type: {type(record)!r}"
        raise TypeError(msg)

    payload = _record_to_mapping(record)
    record_type = str(payload["record_type"])
    validate_known_record_type(record_type)
    validate_ledger_record_contract(payload)

    previous_hash = fetch_ledger_tip_hash(conn)
    body = record_body_for_chain_hash(payload)
    try:
        current_hash = compute_ledger_link_hash(
            previous_hash=previous_hash,
            record=body,
        )
    except Exception as exc:
        from praetor.hashing.canonical import CanonicalSerializationError

        if isinstance(exc, CanonicalSerializationError):
            msg = "ledger record body is not canonically serializable"
            raise LedgerChainIntegrityError(msg) from exc
        raise

    if record_type == "decision_edict":
        payload["ledger_previous_hash"] = previous_hash
        payload["ledger_current_hash"] = current_hash

    record_json = canonical_serialize(payload).decode("utf-8")

    cursor = conn.execute(
        """
        INSERT INTO ledger_chain (
            record_type, record_json, ledger_previous_hash, ledger_current_hash
        ) VALUES (?, ?, ?, ?)
        """,
        (record_type, record_json, previous_hash, current_hash),
    )
    chain_sequence_raw = cursor.lastrowid
    if chain_sequence_raw is None:
        msg = "ledger append did not return chain_sequence"
        raise RuntimeError(msg)
    chain_sequence = int(chain_sequence_raw)
    return LedgerAppendResult(
        chain_sequence=chain_sequence,
        record_type=record_type,
        ledger_previous_hash=previous_hash,
        ledger_current_hash=current_hash,
        record_json=record_json,
    )
