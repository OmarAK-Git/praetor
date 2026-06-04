"""Task 10 — hash-valid rows with incomplete contracts must fail verification."""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from praetor.hashing.canonical import canonical_serialize
from praetor.hashing.domains import compute_ledger_link_hash
from praetor.ledger.hash_chain import (
    LedgerChainIntegrityError,
    record_body_for_chain_hash,
    verify_ledger_chain,
)
from praetor.ledger.store import append_ledger_record
from praetor.state.sqlite_guard import critical_transaction


def _insert_hash_valid_row(
    conn: sqlite3.Connection,
    *,
    record_type: str,
    body: dict[str, Any],
    previous_hash: str | None = None,
) -> None:
    chain_body = record_body_for_chain_hash(body)
    current_hash = compute_ledger_link_hash(
        previous_hash=previous_hash,
        record=chain_body,
    )
    if record_type == "decision_edict":
        stored = {
            **body,
            "ledger_previous_hash": previous_hash,
            "ledger_current_hash": current_hash,
        }
    else:
        stored = body
    record_json = canonical_serialize(stored).decode("utf-8")
    conn.execute(
        """
        INSERT INTO ledger_chain (
            record_type, record_json, ledger_previous_hash, ledger_current_hash
        ) VALUES (?, ?, ?, ?)
        """,
        (record_type, record_json, previous_hash, current_hash),
    )


@pytest.mark.parametrize(
    ("record_type", "incomplete_body"),
    [
        (
            "directive_revocation",
            {"schema_version": "1", "record_type": "directive_revocation"},
        ),
        (
            "never_contain_snapshot",
            {"schema_version": "1", "record_type": "never_contain_snapshot"},
        ),
        (
            "emergency_never_contain",
            {"schema_version": "1", "record_type": "emergency_never_contain"},
        ),
        (
            "decision_edict",
            {
                "schema_version": "1",
                "record_type": "decision_edict",
                "ledger_previous_hash": None,
            },
        ),
    ],
)
def test_hash_valid_incomplete_contract_fails_verification(
    conn: sqlite3.Connection,
    record_type: str,
    incomplete_body: dict[str, Any],
) -> None:
    _insert_hash_valid_row(conn, record_type=record_type, body=incomplete_body)
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError, match="contract validation"):
        verify_ledger_chain(conn)


def test_ad_hoc_invalid_directive_revocation_repro_fails(
    conn: sqlite3.Connection,
) -> None:
    """Reproduces PASSED_INVALID_CONTRACT: hash-valid but contract-incomplete row."""
    body = {"schema_version": "1", "record_type": "directive_revocation"}
    _insert_hash_valid_row(conn, record_type="directive_revocation", body=body)
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError):
        verify_ledger_chain(conn)


def test_append_rejects_model_construct_invalid_record(
    conn: sqlite3.Connection,
) -> None:
    from praetor.contracts.ledger import DirectiveRevocationRecord

    invalid = DirectiveRevocationRecord.model_construct(
        schema_version="1",
        record_type="directive_revocation",
        revocation_id="rev-bad",
    )
    with critical_transaction(conn):
        with pytest.raises(LedgerChainIntegrityError, match="contract validation"):
            append_ledger_record(conn, invalid)
